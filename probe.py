"""One-off check of outside live-score feeds for South African games (run in GitHub Actions).
Writes data/_probe.json with what each feed returned."""
import json

import requests

from common import DATA, save_json

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0 Safari/537.36", "Accept": "application/json, text/html"}
URLS = [
    "https://prod-public-api.livescore.com/v1/api/app/date/soccer/20261011/2",
    "https://prod-public-api.livescore.com/v1/api/app/date/soccer/20261011/2?MD=1",
    "https://prod-public-api.livescore.com/v1/api/app/date/soccer/20261011/0?MD=1",
    "https://prod-public-api.livescore.com/v1/api/app/stage/soccer/south-africa/championship/2?MD=1",
    "https://prod-public-api.livescore.com/v1/api/app/stage/soccer/south-africa/premiership/2?MD=1",
    "https://www.livescore.com/en/football/team/gomora-united/374787/results/",
    "https://www.fotmob.com/api/matches?date=20261011",
    "https://site.api.espn.com/apis/site/v2/sports/soccer/rsa.2/scoreboard?dates=20261011",
    "https://site.api.espn.com/apis/site/v2/sports/soccer/rsa.1/scoreboard?dates=20261011",
    "https://www.sofascore.com/api/v1/sport/football/scheduled-events/2026-10-11",
    "https://api.sofascore.app/api/v1/sport/football/scheduled-events/2026-10-11",
]
out = []
for u in URLS:
    try:
        r = requests.get(u, headers=UA, timeout=30)
        t = r.text
        low = t.lower()
        i = low.find("gomora")
        out.append({"url": u, "status": r.status_code, "size": len(t), "gomora": i >= 0,
                    "around": t[max(0, i - 600): i + 900] if i >= 0 else t[:300]})
    except Exception as e:
        out.append({"url": u, "error": str(e)})
save_json(DATA / "_probe.json", out)
print(json.dumps([{k: v for k, v in o.items() if k != "around"} for o in out], indent=1))
