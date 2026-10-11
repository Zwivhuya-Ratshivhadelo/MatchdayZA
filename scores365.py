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
    return {"slug": slug, "date": g.get("startTime"), "home": g["homeCompetitor"]["name"],
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


def _same_club(a, b):
    a, b = slugify(a).replace("-fc", ""), slugify(b).replace("-fc", "")
    return a == b or a.startswith(b) or b.startswith(a) or difflib.SequenceMatcher(None, a, b).ratio() >= 0.75


def find(feed, m):
    day = (m.get("date") or "")[:10]
    for g in feed:
        if (g["date"] or "")[:10] == day and _same_club(g["home"], m["home"]) and _same_club(g["away"], m["away"]):
            return g
    return None
