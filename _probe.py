import requests, json
H = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.365scores.com/", "Origin": "https://www.365scores.com"}
B = "https://webws.365scores.com/web"; P = "appTypeId=5&langId=1&timezoneName=Africa/Johannesburg"
j = lambda u: requests.get(u, headers=H, timeout=25).json()
d = j(f"{B}/games/results/?{P}&competitions=624")
g0 = next(g for g in d["games"] if "Sundowns" in g["awayCompetitor"]["name"])
print("GAME KEYS", sorted(g0.keys())); print("COMP KEYS", sorted(g0["homeCompetitor"].keys()))
print({k: g0.get(k) for k in ["id","seasonNum","stageNum","groupNum","roundNum","roundName","stageName","statusGroup","statusText","startTime","aggregatedScore","winDescription","hasLineups","hasStats"]})
print("home comp", {k: g0["homeCompetitor"].get(k) for k in ["id","name","shortName","longName","countryId","imageVersion","nameForURL","symbolicName","aggregatedScore"]})
# paging depth / seasons
url, seen, pages = f"{B}/games/results/?{P}&competitions=624", [], 0
while url and pages < 12:
    pages += 1; x = j(url); gs = x.get("games", [])
    if gs: seen.append((gs[-1]["startTime"][:10], gs[0]["startTime"][:10], gs[-1].get("seasonNum"), len(gs)))
    p = (x.get("paging") or {}).get("previousPage"); url = f"https://webws.365scores.com{p}" if p else None
print("PAGES", seen)
gd = j(f"{B}/game/?{P}&gameId={g0['id']}")["game"]
print("DETAIL KEYS", sorted(gd.keys()))
print("members", gd.get("members", [])[:3])
hc = gd["homeCompetitor"]; print("HC KEYS", sorted(hc.keys()))
lu = hc.get("lineups"); print("LINEUPS", json.dumps(lu)[:1500] if lu else None)
print("EVENTS", json.dumps(gd.get("events", [])[:4])[:1500])
print("VENUE", gd.get("venue"))
st = j(f"{B}/game/stats/?{P}&games={g0['id']}"); print("STATS", [(s.get("name"), s.get("value"), s.get("competitorId")) for s in st.get("statistics", [])][:12])
s = j(f"{B}/standings/?{P}&competitions=624"); print("STANDINGS", json.dumps(s)[:800])
img = f"https://imagecache.365scores.com/image/upload/f_png,w_64,h_64,c_limit,q_auto:eco,dpr_2,d_Competitors:default1.png/v{g0['homeCompetitor'].get('imageVersion',1)}/Competitors/{g0['homeCompetitor']['id']}"
r = requests.get(img, headers=H, timeout=25); print("IMG", r.status_code, r.headers.get("content-type"), len(r.content))
c = j(f"{B}/games/current/?{P}&competitions=627"); print("CURRENT 627 count", len(c["games"]), "stages", {(g.get("stageNum"), g.get("roundNum"), g.get("roundName")) for g in c["games"]})
