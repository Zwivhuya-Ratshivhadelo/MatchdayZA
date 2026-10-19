import requests, json, re
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36", "Accept": "application/json,text/html"}
def get(u, **k):
    try:
        r = requests.get(u, headers=H, timeout=30, **k); return r.status_code, r
    except Exception as e: return 0, str(e)
print("===== ESPN")
for lg in ["caf.champions", "caf.confed"]:
    c, r = get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/scoreboard?dates=20261016-20261019")
    print(lg, c)
    if c != 200: print(r.text[:300] if hasattr(r,'text') else r); continue
    evs = r.json().get("events", [])
    print(" events", len(evs))
    for e in evs[:20]: print("  ", e["id"], e["date"], e["name"], e["status"]["type"]["name"], [x.get("score") for x in e["competitions"][0]["competitors"]])
    sa = [e for e in evs if any(k in e["name"] for k in ("Sundowns", "Pirates", "Chiefs", "Durban"))]
    for e in sa[:2]:
        c, s = get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/summary?event={e['id']}")
        j = s.json()
        print(" SUMMARY", e["name"], c, sorted(j.keys()))
        print("  rosters", [(t.get("team",{}).get("displayName"), len(t.get("roster",[]))) for t in j.get("rosters", [])])
        if j.get("rosters"): print("  roster sample", json.dumps(j["rosters"][0].get("roster",[])[:2])[:600])
        print("  boxscore", json.dumps(j.get("boxscore",{}).get("teams",[{}])[0].get("statistics",[]))[:700])
        print("  keyEvents", [(k.get("clock",{}).get("displayValue"), k.get("type",{}).get("text"), k.get("text","")[:80]) for k in j.get("keyEvents",[])][:12])
        print("  commentary", len(j.get("commentary",[])), [c.get("text","")[:80] for c in j.get("commentary",[])[:3]])
        print("  gameInfo", j.get("gameInfo",{}).get("venue",{}).get("fullName"))
print("===== FOTMOB")
c, r = get("https://www.fotmob.com/api/search/suggest?term=caf%20champions")
print(c, r.text[:800] if hasattr(r,'text') else r)
c, r = get("https://www.fotmob.com/api/matches?date=20261018")
print("matches", c)
if c == 200:
    for lg in r.json().get("leagues", []):
        if "CAF" in lg.get("name","") or "Africa" in lg.get("ccode",""): print(" ", lg.get("id"), lg.get("name"), [(m["home"]["name"], m["away"]["name"], m["id"]) for m in lg.get("matches",[])][:6])
print("===== CAF official")
for u in ["https://www.cafonline.com/caf-champions-league/fixtures-results/", "https://www.cafonline.com/"]:
    c, r = get(u); print(u, c, (re.sub(r"\s+"," ", r.text)[:300] if hasattr(r,'text') else r))
    if hasattr(r,'text'): print(" api hints", sorted(set(re.findall(r'https?://[a-z0-9.-]+/[^"\' ]*(?:api|json|feed)[^"\' ]*', r.text)))[:20])
