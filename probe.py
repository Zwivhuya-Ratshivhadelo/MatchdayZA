"""One-off check of outside live-score feeds for South African games (run in GitHub Actions).
Writes data/_probe.json with what each feed returned."""
import json
import re

import requests

from common import DATA, save_json

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0 Safari/537.36", "Accept": "application/json, text/html"}
out = {}
r = requests.get("https://www.livescore.com/en/football/team/gomora-united/374787/results/", headers=UA, timeout=30)
m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S)
nd = json.loads(m.group(1)) if m else {}
out["buildId"] = nd.get("buildId")
txt = json.dumps(nd)
out["pageProps_keys"] = list(nd.get("props", {}).get("pageProps", {}).keys())
hits = [mm.start() for mm in re.finditer("Upington", txt)]
out["hits"] = len(hits)
out["around"] = [txt[max(0, h - 1500): h + 800] for h in hits[:2]]
# event ids near the match
out["eids"] = re.findall(r'"Eid": ?"(\d+)"', txt)[:15]
for eid in out["eids"][:2]:
    for u in [f"https://prod-public-api.livescore.com/v1/api/app/scoreboard/soccer/{eid}?locale=en",
              f"https://prod-public-api.livescore.com/v1/api/app/incidents/soccer/{eid}?locale=en"]:
        try:
            rr = requests.get(u, headers=UA, timeout=30)
            out.setdefault("event_api", []).append({"url": u, "status": rr.status_code, "body": rr.text[:2500]})
        except Exception as e:
            out.setdefault("event_api", []).append({"url": u, "error": str(e)})
save_json(DATA / "_probe.json", out)
print(json.dumps({k: v for k, v in out.items() if k not in ("around", "event_api")}, indent=1))
