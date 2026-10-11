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

import psl
from common import DATA, fetch, load_json, match_key, now_sast, score_line

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
        for f in load_json(DATA / "psl" / f"{slug}.json", {}).get("fixtures", []):
            d = f.get("date") or ""
            if d[:10] != today or "T" not in d:
                continue
            ko = datetime.fromisoformat(d)
            if lo <= ko.hour * 60 + ko.minute < hi:
                games.append({**f, "slug": slug, "kickoff": ko})
    return games


def publish():
    """Push the latest data (only inside GitHub Actions)."""
    if os.environ.get("LIVE_DEPLOY") == "1":
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
    while now_sast() - start < MAX_RUNTIME:
        polls += 1
        now = now_sast()
        links = []
        for slug in {g["slug"] for g in games}:
            try:
                links += psl._detail_links(BeautifulSoup(fetch(f"{psl.BASE}/tournament/{slug}"), "html.parser"))
            except Exception as e:
                print(f"  tournament page failed: {e}")
        for g in games:
            key = match_key(g)
            if key in finished or now < g["kickoff"] - LEAD:
                continue
            link = psl._find_link(links, g["home"], g["away"])
            if not link:
                continue
            try:
                d = psl.parse_detail(fetch(link["url"]))
            except Exception as e:
                print(f"  match page failed {link['url']}: {e}")
                continue
            if not d:
                continue
            if now < g["kickoff"] and not d["events"]:
                # before kick-off: keep the line-ups, mark the fixture with its match page
                d.update(status="NS", minute=None, home_score=None, away_score=None)
                psl.save_match(link["id"], g["slug"], g["home"], g["away"], d)
                psl.store(g["slug"], [], [{**{k: v for k, v in g.items() if k not in ("slug", "kickoff")},
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
    mins = t.hour * 60 + t.minute + 75
    return next((w for w, (lo, hi) in WINDOWS.items() if lo <= mins < hi), "d")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in WINDOWS else window_for_now())
