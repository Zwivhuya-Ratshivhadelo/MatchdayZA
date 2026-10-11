"""Scrape PSL competitions (Premiership, Championship, MTN8, Carling Knockout, Nedbank Cup)
from psl.co.za and store them as JSON in data/psl/<slug>.json.

Run:  python psl.py
"""
import re
import sys
from urllib.parse import unquote

from bs4 import BeautifulSoup

from common import (DATA, clean, fetch, load_json, match_key, merge_matches, now_sast,
                    parse_date, save_json, slugify)

BASE = "https://www.psl.co.za"
COMPETITIONS = {
    "betway-premiership": {"name": "Betway Premiership", "short": "Premiership", "league": True},
    "national-first-division": {"name": "Motsepe Foundation Championship", "short": "Championship", "league": True},
    "mtn8": {"name": "MTN8", "short": "MTN8", "league": False},
    "carling-knockout": {"name": "Carling Knockout", "short": "Carling Knockout", "league": False},
    "nedbank-cup": {"name": "Nedbank Cup", "short": "Nedbank Cup", "league": False},
}

SCORE_RE = re.compile(r"^(\d{1,2})\s*[-–]\s*(\d{1,2})$")
VS_RE = re.compile(r"^vs\.?$", re.I)
DATE_RE = re.compile(r"^(\d{1,2})\s+([A-Za-z]{3,9})(?:\s+(\d{4}))?(?:\s+(\d{1,2}:\d{2}))?\s*(?:[-–]\s*(.*))?$")
DETAIL_RE = re.compile(r"/matchcentre/detail/(\d+)-([a-z0-9-]+)", re.I)
CLUB_RE = re.compile(r"/club/([^?#]+)\?league=([\w-]+)", re.I)
SKIP_LINES = {"match summary", "result", "results", "fixtures", "live", "vs"}


def _lines(soup):
    return [clean(t) for t in soup.get_text("\n").split("\n") if clean(t)]


def _detail_links(soup):
    links = []
    for a in soup.find_all("a", href=True):
        m = DETAIL_RE.search(a["href"])
        if m:
            links.append({"id": m.group(1), "slug": m.group(2).lower(),
                          "url": BASE + m.group(0)})
    return links


def _find_link(links, home, away):
    """Match a detail link by its slug, e.g. 'upington-city-vs-pretoria-university'."""
    h, a = slugify(home), slugify(away)
    for l in links:
        if "-vs-" not in l["slug"]:
            continue
        lh, la = l["slug"].split("-vs-", 1)
        if (lh == h or h.startswith(lh) or lh.startswith(h)) and (a.startswith(la) or la.startswith(a)):
            return l
    return None


def parse_matches(html, ref=None):
    """Return (results, fixtures) from any PSL page that lists matches.

    Works on the visible text order: <home> <score|VS> <away> ... <date [time] - venue>.
    """
    soup = BeautifulSoup(html, "html.parser")
    lines, links = _lines(soup), _detail_links(soup)
    results, fixtures = [], []
    for i, line in enumerate(lines):
        score, vs = SCORE_RE.match(line), VS_RE.match(line)
        if not (score or vs) or i == 0 or i + 1 >= len(lines):
            continue
        home, away = lines[i - 1], lines[i + 1]
        if home.lower() in SKIP_LINES or away.lower() in SKIP_LINES or home[0].isdigit():
            continue
        # look ahead for the "dd Mon [yyyy] [hh:mm] - venue" line
        date = venue = None
        for j in range(i + 2, min(i + 8, len(lines))):
            if SCORE_RE.match(lines[j]) or VS_RE.match(lines[j]):
                break
            d = DATE_RE.match(lines[j])
            if d and d.group(2)[:3].lower() in ("jan", "feb", "mar", "apr", "may", "jun", "jul",
                                                "aug", "sep", "oct", "nov", "dec"):
                date = parse_date(d.group(1), d.group(2), d.group(3), d.group(4), ref)
                venue = clean(d.group(5) or "")
                if not venue and j + 1 < len(lines) and not DATE_RE.match(lines[j + 1]) \
                        and lines[j + 1].lower() not in SKIP_LINES:
                    venue = lines[j + 1]
                break
        if not date:
            continue
        m = {"home": home, "away": away, "date": date, "venue": venue or None}
        if score:
            m.update(home_score=int(score.group(1)), away_score=int(score.group(2)), status="FT")
            link = _find_link(links, home, away)
            if link:
                m.update(match_id=link["id"], url=link["url"])
            results.append(m)
        else:
            m["status"] = "NS"
            fixtures.append(m)
    return results, fixtures


def parse_logs(html):
    """Return {league_slug: [rows]} from log tables (rows link to /club/<Name>?league=<slug>)."""
    soup = BeautifulSoup(html, "html.parser")
    logs = {}
    for a in soup.find_all("a", href=True):
        m = CLUB_RE.search(a["href"])
        row = a.find_parent("tr")
        if not m or not row:
            continue
        team = clean(unquote(m.group(1)).replace("_", " "))
        league = m.group(2).lower()
        cells = row.find_all(["td", "th"])
        nums = []
        for c in cells:
            if a in c.find_all("a"):
                continue
            t = clean(c.get_text())
            if re.fullmatch(r"[+-]?\d+", t):
                nums.append(int(t))
        pos = re.match(r"\s*(\d+)", a.get_text())
        entry = {"pos": int(pos.group(1)) if pos else None, "team": team, "club": m.group(1)}
        if len(nums) >= 8:
            p, w, d, l, gf, ga, gd, pts = nums[-8:]
            entry.update(p=p, w=w, d=d, l=l, gf=gf, ga=ga, gd=gd, pts=pts)
        elif len(nums) >= 3:
            p, w, pts = nums[-3:]
            d = pts - 3 * w          # PSL widget only shows P, W, Pts:
            l = p - w - d            # draws and losses follow exactly from them
            if d < 0 or l < 0:
                continue
            entry.update(p=p, w=w, d=d, l=l, pts=pts)
        else:
            continue
        rows = logs.setdefault(league, [])
        if all(r["team"] != team for r in rows):
            rows.append(entry)
    for rows in logs.values():
        rows.sort(key=lambda r: (r["pos"] is None, r["pos"] or 0, -r["pts"]))
        for i, r in enumerate(rows, 1):
            r["pos"] = r["pos"] or i
    return logs


# ---------------- Match pages: timeline events and stats ----------------
MINUTE_RE = re.compile(r"^(\d{1,3})(?:\s*\+\s*(\d{1,2}))?\s*'?$")
GOAL_RE = re.compile(r"^Goal!\s*(.+?)\s(\d+),\s*(.+?)\s(\d+)\.\s*(.+?)\s*\(([^)]+)\)")
OWN_GOAL_RE = re.compile(r"^Own Goal by\s+(.+?),\s*(.+?)\.\s*(.+?)\s(\d+),\s*(.+?)\s(\d+)", re.I)
PEN_SAVED_RE = re.compile(r"^Penalty saved[!.]?\s*(.+?)\s*\(([^)]+)\)", re.I)
PEN_MISSED_RE = re.compile(r"^Penalty missed[!.]?\s*(.+?)\s*\(([^)]+)\)", re.I)
PEN_WON_RE = re.compile(r"^Penalty\s+([^.]+?)\.\s*(.+?)\s+draws a foul", re.I)
CARD_RE = re.compile(r"^(.+?)\s*\(([^)]+)\)\s+is shown the (yellow|red) card", re.I)
SUB_RE = re.compile(r"^Substitution,\s*([^.]+?)\.\s*(.+?)\s+replaces\s+(.+?)(?:\s+because of an injury)?\.?$", re.I)
PERIODS = [(re.compile(r"^(First Half begins|Match begins|Kick[- ]off)", re.I), "kickoff"),
           (re.compile(r"^First Half ends", re.I), "half_time"),
           (re.compile(r"^Second Half begins", re.I), "second_half"),
           (re.compile(r"^(Second Half ends|Match ends|Full time)", re.I), "full_time"),
           (re.compile(r"^(First|Second) Half Extra Time begins", re.I), "extra_time"),
           (re.compile(r"^Penalty Shootout begins", re.I), "shootout")]
VAR_RE = re.compile(r"^VAR\b", re.I)
STAT_LABELS = {"possession", "shots", "shots on target", "shots off target", "corners", "offsides",
               "fouls", "yellow cards", "red cards", "saves", "passes", "blocked shots"}


def classify(text):
    """Turn one commentary line into a structured event (facts only), or None if minor."""
    m = GOAL_RE.match(text)
    if m:
        return {"type": "penalty_goal" if "penalty" in text.lower() else "goal", "player": m.group(5).strip(),
                "team": m.group(6).strip(), "score": [int(m.group(2)), int(m.group(4))]}
    m = OWN_GOAL_RE.match(text)
    if m:
        return {"type": "own_goal", "player": m.group(1).strip(), "team": m.group(2).strip(),
                "score": [int(m.group(4)), int(m.group(6))]}
    for rx, kind in ((PEN_SAVED_RE, "penalty_saved"), (PEN_MISSED_RE, "penalty_missed")):
        m = rx.match(text)
        if m:
            return {"type": kind, "player": m.group(1).strip(), "team": m.group(2).strip()}
    m = PEN_WON_RE.match(text)
    if m:
        return {"type": "penalty_won", "team": m.group(1).strip(), "player": m.group(2).strip()}
    m = CARD_RE.match(text)
    if m:
        kind = "second_yellow" if "second yellow" in text.lower() else m.group(3).lower()
        return {"type": kind, "player": m.group(1).strip(), "team": m.group(2).strip()}
    m = SUB_RE.match(text)
    if m:
        return {"type": "sub", "team": m.group(1).strip(), "player_in": m.group(2).strip(), "player_out": m.group(3).strip()}
    for rx, kind in PERIODS:
        if rx.match(text):
            return {"type": kind}
    if VAR_RE.match(text):
        return {"type": "var"}
    return None


def _lines_of(node):
    return [clean(t) for t in node.get_text("\n").split("\n") if clean(t)] if node else []


def parse_detail(html):
    """Score, status, minute, key events (newest first), stats and line-ups from a match page."""
    soup = BeautifulSoup(html, "html.parser")
    scores = [clean(x.get_text()) for x in soup.select(".widget-game-result__score-result")]
    if len(scores) >= 2 and scores[0].isdigit() and scores[1].isdigit():
        hs, as_ = int(scores[0]), int(scores[1])
    else:  # fallback: a "2 - 1" line anywhere on the page
        m = next((SCORE_RE.match(l) for l in _lines_of(soup) if SCORE_RE.match(l)), None)
        if not m:
            return None
        hs, as_ = int(m.group(1)), int(m.group(2))
    label_el = soup.select_one(".match-status")
    label = clean(label_el.get_text()) if label_el else ""

    # commentary (minute line, then its text), newest first
    lines = _lines_of(soup.select_one("#widget-tabbed-live-commentary")) or _lines_of(soup)
    events, minute = [], None
    for i, l in enumerate(lines[:-1]):
        mm = MINUTE_RE.match(l)
        if not mm or int(mm.group(1)) > 130:
            continue
        mlabel = mm.group(1) + (f"+{mm.group(2)}" if mm.group(2) else "") + "'"
        minute = minute or mlabel
        ev = classify(lines[i + 1])
        if ev:
            events.append({"minute": mlabel, **ev})

    # stats: "<home> <label> <away>"
    st_lines = _lines_of(soup.select_one("#widget-tabbed-match-statistics"))
    stats = []
    for i in range(1, len(st_lines) - 1):
        lab = st_lines[i]
        if (re.fullmatch(r"\d+(\.\d+)?%?", st_lines[i - 1]) and re.fullmatch(r"\d+(\.\d+)?%?", st_lines[i + 1])
                and not re.fullmatch(r"[\d.%]+", lab) and all(x["label"] != lab for x in stats)):
            stats.append({"label": lab, "home": st_lines[i - 1], "away": st_lines[i + 1]})

    # line-ups
    lineups = []
    for tbl in soup.select("table.line-ups"):
        name_el = tbl.select_one(".name")
        team = {"team": clean(name_el.get_text()) if name_el else "", "starting": [], "subs": []}
        section = "starting"
        for el in tbl.select(".line-ups-sub-heading .heading, td.player"):
            if "heading" in (el.get("class") or []):
                section = "subs" if "sub" in el.get_text().lower() else "starting"
                continue
            no, nm, pos = el.select_one(".player-number"), el.select_one(".team-meta__name"), el.select_one(".position")
            if nm:
                team[section].append({"no": clean(no.get_text()) if no else "", "name": clean(nm.get_text()),
                                      "pos": clean(pos.get_text()) if pos else ""})
        if team["starting"] or team["subs"]:
            lineups.append(team)

    finished = label.lower() in ("result", "full time", "ft") or any(e["type"] == "full_time" for e in events[:4])
    if not finished and MINUTE_RE.match(label):
        minute = label if label.endswith("'") else label + "'"
    return {"home_score": hs, "away_score": as_, "status": "FT" if finished else "LIVE",
            "minute": None if finished else minute, "events": events, "stats": stats, "lineups": lineups}


def latest_line(events):
    """Short text for the newest key event (our wording, built from the facts)."""
    for e in events:
        t, p, team = e["type"], e.get("player", ""), e.get("team", "")
        text = {"goal": f"Goal, {p} ({team})", "penalty_goal": f"Penalty scored, {p} ({team})",
                "own_goal": f"Own goal, {p} ({team})", "penalty_saved": f"Penalty saved, {p} ({team}) denied",
                "penalty_missed": f"Penalty missed, {p} ({team})", "penalty_won": f"Penalty to {team}",
                "red": f"Red card, {p} ({team})", "second_yellow": f"Second yellow, {p} ({team}) sent off",
                "yellow": f"Yellow card, {p} ({team})",
                "sub": f"Sub, {team}: {e.get('player_in')} on for {e.get('player_out')}",
                "half_time": "Half-time", "second_half": "Second half under way", "full_time": "Full time",
                "kickoff": "Kick-off"}.get(t)
        if text:
            return f"{e['minute']} {text}"
    return None


def save_match(match_id, slug, home, away, detail):
    save_json(DATA / "psl" / "matches" / f"{match_id}.json", {
        "match_id": match_id, "comp": slug, "home": home, "away": away,
        "updated": now_sast().isoformat(timespec="seconds"), **detail})


def fetch_missing_details(limit=60):
    """Fetch match pages for finished results that have no saved timeline yet."""
    done = 0
    for slug in COMPETITIONS:
        comp = load_json(DATA / "psl" / f"{slug}.json", {})
        for r in reversed(comp.get("results", [])):
            mid, url = r.get("match_id"), r.get("url")
            if not mid or not url or (DATA / "psl" / "matches" / f"{mid}.json").exists():
                continue
            if done >= limit:
                return
            try:
                html = fetch(url)
                d = parse_detail(html)
            except Exception as e:
                print(f"  match page failed {url}: {e}")
                continue
            done += 1
            if d:
                save_match(mid, slug, r["home"], r["away"], d)
                print(f"  timeline saved: {r['home']} v {r['away']} ({len(d['events'])} events)")
            else:
                print(f"  no timeline found on {url}")
                sample = DATA / "psl" / "_match_page_sample.html"
                if not sample.exists():  # keep one copy to diagnose the page layout
                    sample.write_text(html, encoding="utf-8")


def _teams_of(html):
    soup = BeautifulSoup(html, "html.parser")
    return [clean(x.get_text()) for x in soup.select(".widget-game-result__team-name")][:2]


def fill_by_match_id():
    """League match pages have running numbers (8 games a round). When some clubs have fewer
    results than games played, read the numbers we don't have yet, so goal difference adds up.
    These extra games are kept apart (their match page has no date) and only feed the log."""
    for slug, meta in COMPETITIONS.items():
        if not meta["league"]:
            continue
        path = DATA / "psl" / f"{slug}.json"
        comp = load_json(path, {})
        log = comp.get("log", [])
        teams = {slugify(r["team"]): r["team"] for r in log}
        results = [r for r in comp.get("results", []) if r.get("status") == "FT"]
        known = {r["match_id"] for r in comp.get("results", []) + comp.get("fixtures", []) if r.get("match_id")}
        extra = [e for e in comp.get("extra", []) if e["match_id"] not in known]
        skip = set(comp.get("not_ours", []))
        today = now_sast().date().isoformat()
        checked = {k: v for k, v in comp.get("checked", {}).items() if v == today}   # not played yet, looked at today

        def counts():
            c = {}
            for r in results + extra:
                for t in (r["home"], r["away"]):
                    c[slugify(t)] = c.get(slugify(t), 0) + 1
            return c

        def short():
            c = counts()
            return [r for r in log if c.get(slugify(r["team"]), 0) < r["p"]]

        ids = sorted(int(i) for i in known if str(i).isdigit())
        if not ids or not short():
            continue
        first = ids[0]
        # rough date per round, from the games we do have
        round_dates = {}
        for r in results:
            if str(r.get("match_id", "")).isdigit():
                round_dates.setdefault((int(r["match_id"]) - first) // 8, []).append(r["date"])
        top = first + len(teams) * (len(teams) - 1) - 1   # every number in the season
        have = known | {e["match_id"] for e in extra} | skip | set(checked)
        for mid in range(first, top + 1):
            if not short():
                break
            if str(mid) in have or mid in have:
                continue
            try:
                html = fetch(f"{BASE}/matchcentre/detail/{mid}")
                d, names = parse_detail(html), _teams_of(html)
            except Exception as e:
                print(f"  match {mid} failed: {e}")
                continue
            if len(names) < 2 or slugify(names[0]) not in teams or slugify(names[1]) not in teams:
                skip.add(mid)
                continue
            if not d or d["status"] != "FT":
                checked[str(mid)] = today
                continue
            dates = sorted(round_dates.get((mid - first) // 8, [])) or [""]
            extra.append({"match_id": str(mid), "home": teams[slugify(names[0])], "away": teams[slugify(names[1])],
                          "home_score": d["home_score"], "away_score": d["away_score"], "status": "FT",
                          "date": dates[len(dates) // 2]})
            print(f"  {meta['name']} #{mid}: {names[0]} {d['home_score']}-{d['away_score']} {names[1]}")
        comp["extra"], comp["not_ours"], comp["checked"] = extra, sorted(skip), checked
        save_json(path, comp)
        left = short()
        print(f"{meta['name']}: {len(extra)} extra games; "
              + ("all clubs complete" if not left else "still short: " + ", ".join(r["team"] for r in left)))


def store(slug, results, fixtures, log=None):
    path = DATA / "psl" / f"{slug}.json"
    old = load_json(path, {})
    all_results = merge_matches(old.get("results"), results)
    done = {match_key(r) for r in all_results}
    today = now_sast().date().isoformat()
    all_fixtures = [f for f in merge_matches(old.get("fixtures"), fixtures)
                    if match_key(f) not in done and (f.get("date") or "")[:10] >= today]
    meta = COMPETITIONS[slug]
    save_json(path, {
        "slug": slug, "name": meta["name"], "short": meta["short"], "league": meta["league"],
        "source": f"{BASE}/tournament/{slug}",
        "updated": now_sast().isoformat(timespec="seconds"),
        "log": log if log else old.get("log", []),
        "results": all_results, "fixtures": all_fixtures,
        "extra": old.get("extra", []), "not_ours": old.get("not_ours", []), "checked": old.get("checked", {}),
    })
    return len(all_results), len(all_fixtures)


def run():
    problems = []
    ref = now_sast()
    for slug, meta in COMPETITIONS.items():
        print(f"PSL {meta['name']}")
        try:
            html = fetch(f"{BASE}/tournament/{slug}")
        except Exception as e:
            problems.append(f"{slug}: fetch failed ({e})")
            continue
        results, fixtures = parse_matches(html, ref)
        log = parse_logs(html).get(slug, [])
        if meta["league"] and not log:
            problems.append(f"{slug}: no log rows parsed (page layout changed?)")
        r, f = store(slug, results, fixtures, log)
        print(f"  parsed {len(results)} results, {len(fixtures)} fixtures, {len(log)} log rows"
              f" -> stored {r} results, {f} fixtures")

    # The Match Centre page carries the full Premiership season (all fixtures and results).
    try:
        html = fetch(f"{BASE}/MatchCentre")
        prem = load_json(DATA / "psl" / "betway-premiership.json", {})
        teams = {slugify(t["team"]) for t in prem.get("log", [])}
        results, fixtures = parse_matches(html, ref)
        if teams:  # keep only Premiership matches, in case the page defaults to another cup
            ok = lambda m: slugify(m["home"]) in teams and slugify(m["away"]) in teams
            results, fixtures = [m for m in results if ok(m)], [m for m in fixtures if ok(m)]
        r, f = store("betway-premiership", results, fixtures)
        print(f"Match Centre: +{len(results)} results, +{len(fixtures)} fixtures -> {r}/{f}")
    except Exception as e:
        print(f"Match Centre skipped: {e}")

    # Fill gaps in the season by match number (for goal difference)
    fill_by_match_id()

    # Timelines and stats for finished matches (a few per run, newest first)
    fetch_missing_details()

    if problems:
        print("PROBLEMS:\n  " + "\n  ".join(problems))
        sys.exit(1)


if __name__ == "__main__":
    run()
