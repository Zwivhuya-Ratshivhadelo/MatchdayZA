import requests, json
import caf
B = "https://webws.365scores.com/web"; P = "appTypeId=5&langId=1&timezoneName=Africa/Johannesburg"
H = caf.scores365.HEADERS
j = lambda u: requests.get(u, headers=H, timeout=30).json()
url, found = f"{B}/games/results/?{P}&competitions=624", None
for _ in range(10):
    x = j(url)
    for g in x.get("games", []):
        if g.get("seasonNum") == 66 and g.get("stageName") not in ("Qualifications",) and "Sundowns" in (g["homeCompetitor"]["name"] + g["awayCompetitor"]["name"]):
            found = g; break
    if found: break
    p = (x.get("paging") or {}).get("previousPage"); url = "https://webws.365scores.com" + p
print("GAME", found["id"], found["startTime"], found["homeCompetitor"]["name"], found["awayCompetitor"]["name"], found.get("stageName"))
g = j(f"{B}/game/?{P}&gameId={found['id']}")["game"]
print("members", len(g.get("members", [])), json.dumps(g.get("members", [])[:2])[:500])
lu = g["homeCompetitor"].get("lineups"); print("lineups keys", list((lu or {}).keys())); print(json.dumps((lu or {}).get("members", [])[:3])[:900])
print("events", len(g.get("events", [])), json.dumps(g.get("events", [])[:2])[:600])
m = {"home": caf.club_name(found["homeCompetitor"]["name"]), "away": caf.club_name(found["awayCompetitor"]["name"]), "match_id": f"c{found['id']}"}
caf.DATA = __import__("pathlib").Path("/tmp/x"); d = caf.detail(m)
print("OUR DETAIL events", d["events"][:6]); print(" stats", d["stats"][:6]); print(" lineups", [(t["team"], len(t["starting"]), len(t["subs"]), t["starting"][:3]) for t in d["lineups"]])
for cid in (624, 627):
    s = j(f"{B}/standings/?{P}&competitions={cid}&seasonNum=66")
    print("STANDINGS 66", cid, json.dumps(s)[:1200])
