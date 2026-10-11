"""One-off check of outside live-score feeds for South African games (run in GitHub Actions).
Writes data/_probe.json with what each feed returned."""
import json

import requests

from common import DATA, save_json

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
     "Accept": "*/*", "Referer": "https://www.365scores.com/", "Origin": "https://www.365scores.com"}
URLS = [
    "https://webws.365scores.com/web/games/results/?appTypeId=5&langId=1&timezoneName=Africa/Johannesburg&competitions=5822",
    "https://webws.365scores.com/web/games/current/?appTypeId=5&langId=1&timezoneName=Africa/Johannesburg&competitions=5822",
    "https://webws.365scores.com/web/games/allscores/?appTypeId=5&langId=1&timezoneName=Africa/Johannesburg&startDate=11/10/2026&endDate=11/10/2026&sports=1",
    "https://webws.365scores.com/web/game/?appTypeId=5&langId=1&timezoneName=Africa/Johannesburg&gameId=0&matchupId=77102-90428-5822",
]
out = []
for u in URLS:
    try:
        r = requests.get(u, headers=H, timeout=30)
        b = r.text
        i = b.find("Upington")
        games = []
        try:
            j = r.json()
            for g in j.get("games", []) or ([j["game"]] if j.get("game") else []):
                if g.get("competitionId") == 5822 and g.get("startTime", "")[:10] in ("2026-10-11", "2026-10-10"):
                    games.append(g)
        except Exception:
            pass
        out.append({"url": u, "status": r.status_code, "size": len(b), "upington": i >= 0,
                    "games": games[:3]})
    except Exception as e:
        out.append({"url": u, "error": str(e)})
save_json(DATA / "_probe.json", out)
print(json.dumps([{k: v for k, v in o.items() if k != "around"} for o in out], indent=1))
