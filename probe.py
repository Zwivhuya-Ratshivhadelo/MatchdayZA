"""One-off run in GitHub Actions (starts when this file changes): why some Championship games
get no goal minutes from 365scores."""
import json

import scores365
from common import DATA, load_json, save_json

feed = scores365.games()
comp = load_json(DATA / "psl" / "national-first-division.json", {})
out = {"feed_games": len(feed), "feed_dates": sorted({(g["date"] or "")[:10] for g in feed}), "games": []}
for m in comp.get("results", []):
    if m.get("status") != "FT" or not m.get("match_id"):
        continue
    d = load_json(DATA / "psl" / "matches" / f"{m['match_id']}.json", {}) or {}
    if d.get("events") or (m.get("home_score", 0) + m.get("away_score", 0)) == 0:
        continue
    x = scores365.find(feed, m)
    row = {"game": f"{m['date'][:10]} {m['home']} {m['home_score']}-{m['away_score']} {m['away']}",
           "found": f"{x['date'][:10]} {x['home']} {x['home_score']}-{x['away_score']} {x['away']} id {x['id']}" if x else None}
    if x:
        row["events"] = len(scores365.events(x["id"], x["home"], x["away"], m["home"], m["away"]))
    else:
        row["same_day"] = [f"{g['home']} v {g['away']}" for g in feed if (g["date"] or "")[:10] == m["date"][:10]]
    out["games"].append(row)
save_json(DATA / "_probe.json", out)
