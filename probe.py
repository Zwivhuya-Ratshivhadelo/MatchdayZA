"""One-off run in GitHub Actions (starts when this file changes): what 365scores' game detail
holds for a finished Championship game (goals, scorers, line-ups)."""
import json

import requests

from common import DATA, save_json
from scores365 import HEADERS

r = requests.get("https://webws.365scores.com/web/game/?appTypeId=5&langId=1&timezoneName=Africa/Johannesburg&gameId=4813791",
                 headers=HEADERS, timeout=60)
g = r.json().get("game", {})
out = {"status": r.status_code, "keys": list(g.keys()),
       "events": g.get("events", [])[:12],
       "members": [{k: m.get(k) for k in ("id", "name", "shortName", "competitorId", "jerseyNumber")} for m in g.get("members", [])][:40],
       "home_lineup_keys": list((g.get("homeCompetitor", {}).get("lineups") or {}).keys()),
       "home_lineup_sample": json.dumps(g.get("homeCompetitor", {}).get("lineups"))[:1500],
       "stats": json.dumps(g.get("statistics") or g.get("stats"))[:800]}
save_json(DATA / "_probe.json", out)
