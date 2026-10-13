"""Match-day loop for PSL games. Starts 75 minutes before kick-off so line-ups appear as soon as
the PSL publishes them, then polls psl.co.za every minute during the game, saving score, key
moments, stats and line-ups to data/ and pushing them every couple of minutes.

Run:  python live.py a   (games kicking off before 15:30 SAST)
      python live.py b   (15:30 to 17:29)
      python live.py c   (17:30 to 19:29)
      python live.py d   (19:30 or later)
"""
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta

from bs4 import BeautifulSoup

import build
import psl
import scores365
from common import DATA, fetch, load_json, match_key, now_sast, save_json, score_line

WINDOWS = {"a": (0, 15 * 60 + 30), "b": (15 * 60 + 30, 17 * 60 + 30),
           "c": (17 * 60 + 30, 19 * 60 + 30), "d": (19 * 60 + 30, 24 * 60)}
LEAD = timedelta(minutes=75)                                  # start this long before kick-off
POLL_LIVE = int(os.environ.get("POLL_SECONDS", "60"))         # during games
POLL_PRE = 300                                                # before kick-off (line-ups)
PUBLISH_EVERY = int(os.environ.get("PUBLISH_EVERY", "2"))     # polls between data pushes
MAX_RUNTIME = timedelta(hours=5, minutes=40)                  # GitHub job limit is 6h
MATCH_LENGTH = timedelta(minutes=125)


def todays_games(window):
    lo, hi = WINDOWS[window]
    today = now_sast().date().isoformat()
    games = []
    for slug in psl.COMPETITIONS:
        comp = load_json(DATA / "psl" / f"{slug}.json", {})
        # fixtures, plus games already under way (picked up again after a hand-over)
        for f in comp.get("fixtures", []) + [r for r in comp.get("results", []) if r.get("status") == "LIVE"]:
            d = f.get("date") or ""
            if d[:10] != today or "T" not in d:
                continue
            ko = datetime.fromisoformat(d)
            if lo <= ko.hour * 60 + ko.minute < hi:
                games.append({**f, "slug": slug, "kickoff": ko})
    return games


IDS_PATH = DATA / "psl" / "_match_ids.json"   # match page number -> teams, found by looking pages up


def id_link(g, budget):
    """Find a game's match page by its number when no page links to it yet (fixtures have no links).
    League match pages are numbered in a block per season; numbers we already looked at are remembered."""
    ids = load_json(IDS_PATH, {})
    h, a = psl.slugify(g["home"]), psl.slugify(g["away"])
    same = lambda x, y: bool(x) and bool(y) and (x == y or x.startswith(y + "-") or y.startswith(x + "-"))   # "cape-town-city" = "cape-town-city-fc"
    for mid, t in ids.items():
        if same(t.get("home"), h) and same(t.get("away"), a):
            return {"id": mid, "url": f"{psl.BASE}/matchcentre/detail/{mid}"}
    comp = load_json(DATA / "psl" / f"{g['slug']}.json", {})
    known = sorted(int(m["match_id"]) for m in comp.get("results", []) + comp.get("extra", [])
                   if str(m.get("match_id", "")).isdigit())
    if not known:
        return None
    first = known[0]
    found = None
    for mid in range(first, first + 260):
        if budget[0] <= 0 or found:
            break
        if str(mid) in ids or mid in known:
            continue
        budget[0] -= 1
        try:
            names = psl._teams_of(fetch(f"{psl.BASE}/matchcentre/detail/{mid}"))
        except Exception as e:
            print(f"  match {mid} failed: {e}")
            continue
        ids[str(mid)] = {"home": psl.slugify(names[0]), "away": psl.slugify(names[1])} if len(names) >= 2 else {}
        if same(ids[str(mid)].get("home"), h) and same(ids[str(mid)].get("away"), a):
            found = {"id": str(mid), "url": f"{psl.BASE}/matchcentre/detail/{mid}"}
    save_json(IDS_PATH, ids)
    return found


def publish():
    """Push the latest data (only inside GitHub Actions)."""
    if os.environ.get("LIVE_DEPLOY") == "1":
        try:
            build.run()
        except Exception as e:
            print(f"  build failed: {e}")
        subprocess.run(["bash", "commit.sh"], check=False)


def run(window):
    games = todays_games(window)
    if not games:
        print(f"No PSL games in window {window} today. Exiting.")
        return
    start = now_sast()
    first_ko = min(g["kickoff"] for g in games)
    last_end = max(g["kickoff"] for g in games) + MATCH_LENGTH
    print("Today's games:", ", ".join(f"{g['home']} v {g['away']} {g['kickoff']:%H:%M}" for g in games))

    wait = (first_ko - LEAD - now_sast()).total_seconds()
    if wait > 0:
        print(f"Sleeping {wait/60:.0f} min until 75 min before kick-off")
        time.sleep(wait)

    finished, polls = set(), 0
    status_path = DATA / "psl" / "_live_status.json"
    while now_sast() - start < MAX_RUNTIME:
        polls += 1
        now = now_sast()
        links = []
        for slug in {g["slug"] for g in games}:
            try:
                links += psl._detail_links(BeautifulSoup(fetch(f"{psl.BASE}/tournament/{slug}"), "html.parser"))
            except Exception as e:
                print(f"  tournament page failed: {e}")
        report = {"time": now.isoformat(timespec="seconds"), "links_found": len(links), "games": []}
        budget = [120]   # match pages we may look up by number in this poll
        feed = None      # 365scores, fetched once per poll when a game has no PSL live coverage
        for g in games:
            key = match_key(g)
            entry = {"game": f"{g['home']} v {g['away']}", "kickoff": g["date"]}
            report["games"].append(entry)
            if key in finished or now < g["kickoff"] - LEAD:
                continue
            link = psl._find_link(links, g["home"], g["away"]) or id_link(g, budget)
            entry["match_page"] = link["url"] if link else None
            if not link:
                continue
            try:
                d = psl.parse_detail(fetch(link["url"]))
            except Exception as e:
                print(f"  match page failed {link['url']}: {e}")
                continue
            entry["page"] = (f"{d['status']} {d['home_score']}-{d['away_score']}, line-ups {len(d['lineups'])}" if d else "nothing yet")
            # the PSL page is live but carries no commentary or stats: take clock, goals and stats from 365scores
            if d and d["status"] == "LIVE" and not d["events"] and not d["stats"]:
                if feed is None:
                    feed = scores365.games()
                x = scores365.find(feed, g)
                entry["365scores"] = f"{x['status']} {x['home_score']}-{x['away_score']} {x['minute'] or ''}" if x else "not found"
                if x and x["status"] in ("LIVE", "FT"):
                    d.update(home_score=x["home_score"], away_score=x["away_score"], status=x["status"], minute=x["minute"],
                             stats=scores365.stats(x["id"], x.get("home_id")),
                             events=scores365.events(x["id"], x["home"], x["away"], g["home"], g["away"]))
            # no live coverage on the PSL page after kick-off: take the score from 365scores
            if (not d or d["status"] == "NS") and now >= g["kickoff"] - timedelta(minutes=5):
                if feed is None:
                    feed = scores365.games()
                x = scores365.find(feed, g)
                entry["365scores"] = f"{x['status']} {x['home_score']}-{x['away_score']} {x['minute'] or ''}" if x else "not found"
                if x and x["status"] in ("LIVE", "FT"):
                    d = {"home_score": x["home_score"], "away_score": x["away_score"], "status": x["status"],
                         "minute": x["minute"], "stats": scores365.stats(x["id"], x.get("home_id")),
                         "lineups": (d or {}).get("lineups", []),
                         "events": scores365.events(x["id"], x["home"], x["away"], g["home"], g["away"])}
            if not d:
                continue
            if d["status"] == "NS" or (now < g["kickoff"] and not d["events"]):
                # before kick-off: keep the line-ups, mark the fixture with its match page
                d.update(status="NS", minute=None, home_score=None, away_score=None)
                psl.drop_live(g["slug"], g)
                psl.save_match(link["id"], g["slug"], g["home"], g["away"], d)
                skip = ("slug", "kickoff", "status", "home_score", "away_score", "minute", "latest")   # a fixture has no score
                psl.store(g["slug"], [], [{**{k: v for k, v in g.items() if k not in skip},
                                           "match_id": link["id"], "url": link["url"]}])
                print(f"  {g['home']} v {g['away']}: pre-match, line-ups {'in' if d['lineups'] else 'not out yet'}")
                continue
            psl.save_match(link["id"], g["slug"], g["home"], g["away"], d)
            m = {"home": g["home"], "away": g["away"], "date": g["date"], "venue": g.get("venue"),
                 "match_id": link["id"], "url": link["url"], "latest": psl.latest_line(d["events"]),
                 **{k: d[k] for k in ("home_score", "away_score", "status", "minute")}}
            psl.store(g["slug"], [m], [])
            if d["status"] == "FT":
                finished.add(key)
            print(f"  {score_line(m)} {d['status']} {d['minute'] or ''} | {m['latest'] or ''}")
        save_json(status_path, report)
        if polls % PUBLISH_EVERY == 0:
            publish()
        if len(finished) == len(games) or now_sast() > last_end + timedelta(minutes=20):
            break
        started = any(now_sast() >= g["kickoff"] - timedelta(minutes=2) for g in games)
        time.sleep(POLL_LIVE if started else POLL_PRE)
    publish()
    print("Live loop done.")


def window_for_now():
    t = now_sast()
    mins = t.hour * 60 + t.minute + 80   # started a little before the 75-minute lead
    return next((w for w, (lo, hi) in WINDOWS.items() if lo <= mins < hi), "d")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in WINDOWS else window_for_now())
