import requests, json
H = {"User-Agent": "Mozilla/5.0"}
B = "https://webws.365scores.com/web"
P = "appTypeId=5&langId=1&timezoneName=Africa/Johannesburg"
def j(u):
    r = requests.get(u, headers=H, timeout=25); return r.json()
for q in ["caf champions league", "caf confederation cup", "champions league africa"]:
    d = j(f"{B}/search/?{P}&query={q.replace(' ','%20')}")
    for c in d.get("competitions", []): print(q, "|", c.get("id"), c.get("name"), c.get("countryId"), c.get("sportId"))
ids = set()
for q in ["caf champions league", "caf confederation cup"]:
    for c in j(f"{B}/search/?{P}&query={q.replace(' ','%20')}").get("competitions", []):
        if c.get("sportId") == 1: ids.add(c["id"])
for cid in sorted(ids):
    for kind in ["current", "results"]:
        d = j(f"{B}/games/{kind}/?{P}&competitions={cid}")
        comps = {c["id"]: c["name"] for c in d.get("competitions", [])}
        gs = d.get("games", [])
        print(f"=== {cid} {comps.get(cid)} {kind} {len(gs)}")
        for g in gs[:60]:
            print(" ", g.get("startTime","")[:16], g.get("statusText"), g["homeCompetitor"]["name"], g["homeCompetitor"].get("score"), "-", g["awayCompetitor"].get("score"), g["awayCompetitor"]["name"], "|", g.get("roundName"), g.get("stageName"), g.get("groupName"), "| cc", g["homeCompetitor"].get("countryId"), g["awayCompetitor"].get("countryId"))
    try:
        d = j(f"{B}/standings/?{P}&competitions={cid}")
        for s in d.get("standings", []):
            print(" STANDINGS", s.get("groupName") or s.get("displayName"), len(s.get("rows", [])))
    except Exception as e: print(" standings err", e)
