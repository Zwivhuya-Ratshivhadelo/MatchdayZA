"""One-off run in GitHub Actions (starts when this file changes): can a web page read 365scores
directly from the visitor's browser (CORS)?"""
import requests

from common import DATA, save_json

out = {}
for origin in ("https://www.matchdayza.co.za", "https://example.com"):
    r = requests.get("https://webws.365scores.com/web/games/current/?appTypeId=5&langId=1&timezoneName=Africa/Johannesburg&competitions=414",
                     headers={"Origin": origin, "User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/126 Mobile Safari/537.36"},
                     timeout=30)
    out[origin] = {"status": r.status_code, "acao": r.headers.get("Access-Control-Allow-Origin"),
                   "acac": r.headers.get("Access-Control-Allow-Credentials"), "vary": r.headers.get("Vary"),
                   "games": [f"{g['homeCompetitor']['name']} {g['homeCompetitor'].get('score')}-{g['awayCompetitor'].get('score')} "
                             f"{g['awayCompetitor']['name']} {g.get('shortStatusText')} {g.get('gameTimeDisplay')}"
                             for g in r.json().get("games", [])[:6]] if r.ok else r.text[:200]}
    opt = requests.options("https://webws.365scores.com/web/games/current/", headers={"Origin": origin,
                           "Access-Control-Request-Method": "GET"}, timeout=30)
    out[origin]["preflight"] = {"status": opt.status_code, "acao": opt.headers.get("Access-Control-Allow-Origin")}
save_json(DATA / "_probe.json", out)
