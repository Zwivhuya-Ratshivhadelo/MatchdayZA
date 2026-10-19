"""CAF Champions League and CAF Confederation Cup from 365scores (every game of the current season),
stored like the PSL competitions in data/psl/<slug>.json, with each game's goals, stats and line-ups
in data/psl/matches/c<game id>.json. Clubs' crests go to logos/<club>.png (PSL crests are kept).

    run()                  -> update both competitions (normal hourly update)
    refresh(slug, match)   -> fetch one game now (used by live.py while it is on)

Run:  python caf.py
"""
import re
import sys

import requests

import scores365
from common import DATA, ROOT, load_json, now_sast, save_json, slugify

COMPETITIONS = {
    "caf-champions-league": {"id": 624, "name": "CAF Champions League"},
    "caf-confederation-cup": {"id": 627, "name": "CAF Confederation Cup"},
}
SOUTH_AFRICA = 134   # 365scores country id
API = "https://webws.365scores.com/web"
QS = "appTypeId=5&langId=1&timezoneName=Africa/Johannesburg"
LOGO = ("https://imagecache.365scores.com/image/upload/f_png,w_128,h_128,c_limit,q_auto:eco,"
        "d_Competitors:default1.png/v{v}/Competitors/{id}")
DETAILS_PER_RUN = 40

# names as the clubs are known here (PSL clubs keep the PSL's spelling, so their pages link up)
NAMES = {"cffa": "CFFA", "kabuscorp-sc": "Kabuscorp SC", "15-de-agosto": "15 de Agosto",
         "primeiro-de-agosto": "Primeiro de Agosto"}
UPPER = {"sc", "fc", "ac", "as", "cs", "cr", "usm", "mc", "rsb", "asec", "tp", "afad", "asko", "dc", "zed",
         "js", "js", "ca", "es", "us", "ud", "cd", "apr", "afc", "ssc", "fus", "asfar", "far", "ase", "uds"}


def club_name(raw):
    s = slugify(raw)
    if s in NAMES:
        return NAMES[s]
    words = []
    for w in re.sub(r"\bF\.C\.?", "FC", raw or "").split():
        bare = re.sub(r"[^A-Za-z]", "", w).lower()
        if bare in UPPER:
            words.append(w.upper())
        elif w[:1].islower() and w.lower() not in ("de", "da", "do", "du", "des", "el", "al"):
            words.append(w[:1].upper() + w[1:])
        else:
            words.append(w)
    return " ".join(words)


def get(path):
    r = requests.get(f"{API}/{path}{'&' if '?' in path else '?'}{QS}", headers=scores365.HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def norm(g):
    """A 365scores game as one of our matches."""
    x = scores365._norm(g, "")
    h, a = g["homeCompetitor"], g["awayCompetitor"]
    m = {"home": club_name(h["name"]), "away": club_name(a["name"]), "date": g.get("startTime"),
         "match_id": f"c{g['id']}", "status": x["status"]}
    if x["status"] != "NS":
        m.update(home_score=x["home_score"], away_score=x["away_score"])
    if x["status"] == "LIVE":
        m["minute"] = x["minute"]
    if SOUTH_AFRICA in (h.get("countryId"), a.get("countryId")):
        m["sa"] = True
    return m


def season_games(cid):
    """Every game of the current season: what's coming up, then results page by page (newest first)."""
    cur = get(f"games/current/?competitions={cid}").get("games", [])
    season = max((g.get("seasonNum") or 0 for g in cur), default=0)
    games = {g["id"]: g for g in cur}
    page, pages = f"games/results/?competitions={cid}", 0
    while page and pages < 10:
        pages += 1
        j = get(page)
        rows = j.get("games", [])
        season = season or max((g.get("seasonNum") or 0 for g in rows), default=0)
        mine = [g for g in rows if g.get("seasonNum") == season]
        for g in mine:
            games.setdefault(g["id"], g)
        if len(mine) < len(rows):   # reached last season
            break
        prev = (j.get("paging") or {}).get("previousPage")
        page = prev.split("/web/", 1)[1] if prev else None
    return [g for g in games.values() if g.get("seasonNum") == season]


def save_logo(c):
    path = ROOT / "logos" / f"{slugify(club_name(c['name']))}.png"
    if path.exists():
        return
    try:
        r = requests.get(LOGO.format(v=c.get("imageVersion") or 1, id=c["id"]), headers=scores365.HEADERS, timeout=30)
        if r.ok and r.headers.get("content-type", "").startswith("image") and len(r.content) > 500:
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(r.content)
    except requests.RequestException:
        pass


def lineups(g):
    """Starting XI and substitutes for both clubs, when the feed has them."""
    people = {p.get("id"): p for p in g.get("members", []) if p.get("id")}
    out = []
    for side in ("homeCompetitor", "awayCompetitor"):
        c = g.get(side) or {}
        lu = (c.get("lineups") or {}).get("members") or []
        start, subs = [], []
        for p in lu:
            who = people.get(p.get("id"), {})
            row = {"no": who.get("jerseyNumber") or "", "name": who.get("name") or "",
                   "pos": ((p.get("position") or {}).get("shortName") or (p.get("position") or {}).get("name") or "")}
            if not row["name"]:
                continue
            text = (p.get("statusText") or "").lower()
            (start if p.get("status") == 1 or text.startswith("start") else subs).append(row)
        if start:
            out.append({"team": club_name(c.get("name")), "starting": start, "subs": subs})
    return out if len(out) == 2 else []


def detail(m):
    """Goals, cards, stats and line-ups of one game, saved for the match page."""
    gid = m["match_id"][1:]
    try:
        g = get(f"game/?gameId={gid}").get("game", {})
    except Exception as e:
        print(f"  game {gid} failed: {e}")
        return None
    h, a = g.get("homeCompetitor", {}), g.get("awayCompetitor", {})
    x = scores365._norm(g, "")
    d = {"home": m["home"], "away": m["away"], "status": x["status"], "minute": x["minute"],
         "home_score": x["home_score"], "away_score": x["away_score"],
         "events": scores365.events(gid, h.get("name"), a.get("name"), m["home"], m["away"]),
         "stats": scores365.stats(gid, h.get("id")), "lineups": lineups(g),
         "venue": (g.get("venue") or {}).get("name") or ""}
    save_json(DATA / "psl" / "matches" / f"{m['match_id']}.json", d)
    return d


def store(slug, games):
    """Write the competition file: results (finished and live) and fixtures, plus group logs."""
    meta = COMPETITIONS[slug]
    path = DATA / "psl" / f"{slug}.json"
    old = load_json(path, {}) or {}
    matches = sorted((norm(g) for g in games), key=lambda m: m.get("date") or "")
    venues = {f"c{g['id']}": (g.get("venue") or {}).get("name") for g in games}
    for m in matches:
        if venues.get(m["match_id"]):
            m["venue"] = venues[m["match_id"]]
    save_json(path, {
        "slug": slug, "name": meta["name"], "short": meta["name"], "league": False,
        "updated": now_sast().isoformat(timespec="seconds"),
        "log": [], "groups": groups(meta["id"]) or old.get("groups", []),
        "results": [m for m in matches if m["status"] in ("FT", "LIVE")],
        "fixtures": [m for m in matches if m["status"] == "NS"],
    })
    return matches


def groups(cid):
    """Group tables once the group stage starts: [{"name": "Group A", "log": [...]}]."""
    try:
        j = get(f"standings/?competitions={cid}")
    except Exception:
        return []
    out = []
    for s in j.get("standings", []):
        names = {x.get("num"): x.get("name") for x in s.get("groups", []) or []}
        by = {}
        for r in s.get("rows", []):
            c = r.get("competitor") or {}
            gf, ga = r.get("for"), r.get("against")
            by.setdefault(r.get("groupNum"), []).append({
                "pos": r.get("position"), "team": club_name(c.get("name")), "p": r.get("gamePlayed", 0),
                "w": r.get("gamesWon", 0), "d": r.get("gamesEven", 0), "l": r.get("gamesLost", 0),
                "gf": gf, "ga": ga, "gd": (gf - ga) if isinstance(gf, (int, float)) and isinstance(ga, (int, float)) else None,
                "pts": r.get("points", 0)})
        for num, rows in sorted(by.items(), key=lambda kv: kv[0] or 0):
            out.append({"name": names.get(num) or (f"Group {chr(64 + num)}" if num else ""),
                        "log": sorted(rows, key=lambda r: r["pos"] or 99)})
    return out


def run():
    problems = []
    for slug, meta in COMPETITIONS.items():
        print(meta["name"])
        try:
            games = season_games(meta["id"])
        except Exception as e:
            problems.append(f"{slug}: {e}")
            continue
        for g in games:
            for side in ("homeCompetitor", "awayCompetitor"):
                save_logo(g[side])
        matches = store(slug, games)
        # details: games on now, and finished games not fetched yet (newest first)
        todo = [m for m in matches if m["status"] == "LIVE"]
        todo += [m for m in reversed(matches) if m["status"] == "FT"
                 and not (DATA / "psl" / "matches" / f"{m['match_id']}.json").exists()]
        for m in todo[:DETAILS_PER_RUN]:
            detail(m)
        print(f"  {sum(m['status'] != 'NS' for m in matches)} results, {sum(m['status'] == 'NS' for m in matches)} fixtures,"
              f" {min(len(todo), DETAILS_PER_RUN)} games' details")
    if problems:
        print("PROBLEMS:\n  " + "\n  ".join(problems))
        sys.exit(1)


def refresh(slug, m):
    """One game now: its details, and its line in the competition file. Returns the game as stored."""
    d = detail(m)
    if not d or d["status"] == "NS":
        return d
    path = DATA / "psl" / f"{slug}.json"
    comp = load_json(path, {}) or {}
    row = {**m, "status": d["status"], "home_score": d["home_score"], "away_score": d["away_score"]}
    row.pop("minute", None)
    if d["status"] == "LIVE":
        row["minute"] = d["minute"]
    comp["fixtures"] = [f for f in comp.get("fixtures", []) if f.get("match_id") != m["match_id"]]
    comp["results"] = sorted([r for r in comp.get("results", []) if r.get("match_id") != m["match_id"]] + [row],
                             key=lambda r: r.get("date") or "")
    save_json(path, comp)
    return d


if __name__ == "__main__":
    run()
