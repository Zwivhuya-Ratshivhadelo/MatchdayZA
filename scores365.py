"""Live scores and results from 365scores for games the PSL doesn't cover live
(the Motsepe Foundation Championship). Public JSON used by their website.

    games()            -> today's / recent Championship games, normalised
    find(games, m)     -> the game matching one of our fixtures (same day, same clubs)
"""
import difflib
import re

import requests

from common import slugify

URL = ("https://webws.365scores.com/web/games/{kind}/?appTypeId=5&langId=1"
       "&timezoneName=Africa/Johannesburg&competitions={comps}")
COMPETITIONS = {"national-first-division": 5822, "betway-premiership": 414, "mtn8": 5821}   # our slug -> 365scores competition
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/126.0 Safari/537.36", "Accept": "application/json",
           "Referer": "https://www.365scores.com/", "Origin": "https://www.365scores.com"}


def _norm(g, slug):
    st = g.get("statusGroup")
    status = "FT" if st == 4 else "LIVE" if st == 3 else "NS"
    text = (g.get("shortStatusText") or g.get("statusText") or "").strip()
    minute = None
    if status == "LIVE":
        if re.search(r"half", text, re.I):
            minute = "HT"
        elif g.get("gameTime") and g["gameTime"] > 0:
            minute = f"{int(g['gameTime'])}'"
    hs, as_ = g["homeCompetitor"].get("score"), g["awayCompetitor"].get("score")
    return {"id": g.get("id"), "slug": slug, "date": g.get("startTime"), "home": g["homeCompetitor"]["name"],
            "away": g["awayCompetitor"]["name"], "status": status, "minute": minute,
            "home_score": int(hs) if hs is not None and hs >= 0 and status != "NS" else None,
            "away_score": int(as_) if as_ is not None and as_ >= 0 and status != "NS" else None}


def games():
    out = {}
    for slug, cid in COMPETITIONS.items():
        for kind in ("current", "results"):
            try:
                r = requests.get(URL.format(kind=kind, comps=cid), headers=HEADERS, timeout=30)
                r.raise_for_status()
                for g in r.json().get("games", []):
                    out[g["id"]] = _norm(g, slug)
            except Exception as e:
                print(f"  365scores {kind} failed: {e}")
    return list(out.values())


EVENT_TYPES = {"goal": "goal", "own goal": "own_goal", "penalty": "penalty_goal",
               "red card": "red", "second yellow card": "second_yellow", "yellow card": "yellow"}


def events(game_id, home, away, home_name, away_name):
    """Key moments (newest first): minute, kind and club. 365scores doesn't name players
    for these games, so only the club is given."""
    try:
        r = requests.get(f"https://webws.365scores.com/web/game/?appTypeId=5&langId=1"
                         f"&timezoneName=Africa/Johannesburg&gameId={game_id}", headers=HEADERS, timeout=30)
        r.raise_for_status()
        g = r.json().get("game", {})
    except Exception as e:
        print(f"  365scores game {game_id} failed: {e}")
        return []
    names = {m.get("id"): m.get("name") for m in g.get("members", []) if m.get("id")}
    teams = {g.get("homeCompetitor", {}).get("id"): home_name, g.get("awayCompetitor", {}).get("id"): away_name}
    out, score = [], [0, 0]
    for e in sorted(g.get("events", []), key=lambda e: e.get("order", 0)):
        et = e.get("eventType", {})
        name, sub = (et.get("name") or "").lower(), (et.get("subTypeName") or "").lower()
        kind = EVENT_TYPES.get(sub) if sub in EVENT_TYPES else EVENT_TYPES.get(name)
        if name == "goal" and "own" in sub:
            kind = "own_goal"
        elif name == "goal" and "penalt" in sub:
            kind = "penalty_goal"
        if not kind:
            continue
        team = teams.get(e.get("competitorId"), "")
        ev = {"minute": e.get("gameTimeDisplay") or f"{int(e.get('gameTime', 0))}'", "type": kind, "team": team,
              "player": names.get(e.get("playerId"), "")}
        if kind in ("goal", "penalty_goal", "own_goal"):
            scorer_home = (team == home_name) != (kind == "own_goal")
            score[0 if scorer_home else 1] += 1
            ev["score"] = list(score)
        out.append(ev)
    return list(reversed(out))


def _same_club(a, b):
    a, b = slugify(a).replace("-fc", ""), slugify(b).replace("-fc", "")
    return a == b or a.startswith(b) or b.startswith(a) or difflib.SequenceMatcher(None, a, b).ratio() >= 0.75


def find(feed, m):
    day = (m.get("date") or "")[:10]
    for g in feed:
        if (g["date"] or "")[:10] == day and _same_club(g["home"], m["home"]) and _same_club(g["away"], m["away"]):
            return g
    return None
