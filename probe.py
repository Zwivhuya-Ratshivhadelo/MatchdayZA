"""One-off run in GitHub Actions (starts when this file changes): list 365scores competitions
for South Africa, so PSL competitions can use it as a backup live source."""
import requests

from common import DATA, save_json
from scores365 import HEADERS

out = {}
for day in ("10/10/2026", "11/10/2026", "13/10/2026", "17/10/2026"):
    r = requests.get("https://webws.365scores.com/web/games/allscores/?appTypeId=5&langId=1"
                     f"&timezoneName=Africa/Johannesburg&startDate={day}&endDate={day}&sports=1", headers=HEADERS, timeout=60)
    j = r.json()
    for c in j.get("competitions", []):
        if c.get("countryId") == 134:
            out[c["id"]] = c.get("name")
    for g in j.get("games", []):
        if g.get("competitionId") in out:
            out.setdefault(f"games-{g['competitionId']}", []).append(
                f"{g['startTime'][:16]} {g['homeCompetitor']['name']} v {g['awayCompetitor']['name']} [{g.get('statusText')}]")
save_json(DATA / "_probe.json", out)
