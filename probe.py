"""One-off check of outside live-score feeds for South African games (run in GitHub Actions).
Writes data/_probe.json with what each feed returned."""
import json

import requests

from common import DATA, save_json

HEADERS = {
    "browser": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
                "Accept": "*/*", "Referer": "https://www.sofascore.com/", "Origin": "https://www.sofascore.com"},
    "app": {"User-Agent": "okhttp/4.12.0", "Accept": "application/json"},
    "plain": {},
}
URLS = [
    "https://api.sofascore.app/api/v1/team/1119880/events/last/0",
    "https://api.sofascore.com/api/v1/team/1119880/events/last/0",
    "https://www.sofascore.com/api/v1/team/1119880/events/last/0",
    "https://api.sofascore.app/api/v1/sport/football/scheduled-events/2026-10-11",
]
out = []
for u in URLS:
    for name, h in HEADERS.items():
        try:
            r = requests.get(u, headers=h, timeout=30)
            body = r.text
            i = body.find("Upington")
            out.append({"url": u, "headers": name, "status": r.status_code, "size": len(body),
                        "upington": i >= 0, "around": body[max(0, i - 1200): i + 1200] if i >= 0 else body[:200]})
        except Exception as e:
            out.append({"url": u, "headers": name, "error": str(e)})
save_json(DATA / "_probe.json", out)
print(json.dumps([{k: v for k, v in o.items() if k != "around"} for o in out], indent=1))
