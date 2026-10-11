"""One-off check of outside live-score feeds for South African games (run in GitHub Actions).
Writes data/_probe.json with what each feed returned for a given day."""
import json
import sys
from datetime import date

import requests

from common import DATA, save_json

DAY = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0 Safari/537.36", "Accept": "application/json"}
out = {"day": DAY}

try:
    r = requests.get(f"https://prod-public-api.livescore.com/v1/api/app/date/soccer/{DAY.replace('-', '')}/2?MD=1",
                     headers=UA, timeout=30)
    out["livescore_status"] = r.status_code
    stages = r.json().get("Stages", []) if r.ok else []
    sa = [s for s in stages if "south africa" in (s.get("Cnm") or "").lower()]
    out["livescore"] = [{"stage": s.get("Snm"), "comp": s.get("CompN") or s.get("Cnm"), "events": [
        {"id": e.get("Eid"), "home": (e.get("T1") or [{}])[0].get("Nm"), "away": (e.get("T2") or [{}])[0].get("Nm"),
         "score": f"{e.get('Tr1')}-{e.get('Tr2')}", "status": e.get("Eps"), "start": e.get("Esd")}
        for e in s.get("Events", [])]} for s in sa]
    if sa and sa[0].get("Events"):
        eid = sa[0]["Events"][0].get("Eid")
        r2 = requests.get(f"https://prod-public-api.livescore.com/v1/api/app/scoreboard/soccer/{eid}?locale=en",
                          headers=UA, timeout=30)
        out["livescore_scoreboard_status"] = r2.status_code
        out["livescore_scoreboard_keys"] = list(r2.json().keys()) if r2.ok else None
        out["livescore_scoreboard_sample"] = json.dumps(r2.json())[:3000] if r2.ok else r2.text[:300]
except Exception as e:
    out["livescore_error"] = str(e)

try:
    r = requests.get(f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{DAY}", headers=UA, timeout=30)
    out["sofascore_status"] = r.status_code
    evs = r.json().get("events", []) if r.ok else []
    out["sofascore"] = [{"id": e["id"], "tournament": e["tournament"]["name"],
                         "country": e["tournament"].get("category", {}).get("name"),
                         "home": e["homeTeam"]["name"], "away": e["awayTeam"]["name"],
                         "score": f"{e.get('homeScore', {}).get('current')}-{e.get('awayScore', {}).get('current')}",
                         "status": e.get("status", {}).get("description")}
                        for e in evs if e["tournament"].get("category", {}).get("name") == "South Africa"]
    if not r.ok:
        out["sofascore_body"] = r.text[:300]
except Exception as e:
    out["sofascore_error"] = str(e)

save_json(DATA / "_probe.json", out)
print(json.dumps(out, indent=2)[:4000])
