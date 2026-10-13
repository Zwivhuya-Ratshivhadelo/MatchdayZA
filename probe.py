"""One-off run in GitHub Actions (starts when this file changes): what match stats 365scores has."""
import json

import requests

import scores365
from common import DATA, save_json
from scores365 import HEADERS

g = next((x for x in scores365.games() if x["home"].startswith("Cape Town City") and x["date"].startswith("2026-10-13")), None)
out = {"game": g}
if g:
    for u in [f"https://webws.365scores.com/web/game/stats/?appTypeId=5&langId=1&timezoneName=Africa/Johannesburg&games={g['id']}",
              f"https://webws.365scores.com/web/game/?appTypeId=5&langId=1&timezoneName=Africa/Johannesburg&gameId={g['id']}"]:
        r = requests.get(u, headers=HEADERS, timeout=30)
        out[u.split("/web/")[1][:12]] = {"status": r.status_code, "body": r.text[:6000]}
save_json(DATA / "_probe.json", out)
