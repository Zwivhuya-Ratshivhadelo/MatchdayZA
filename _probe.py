import requests, json, re
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}
def get(u):
    try:
        r = requests.get(u, headers=H, timeout=30); return r.status_code, r
    except Exception as e: return 0, None
print("===== ESPN")
for lg in ["caf.champions", "caf.confed", "caf.champions_league", "caf.confederations"]:
    for q in ["", "?dates=20261018", "?dates=20261017"]:
        c, r = get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/scoreboard{q}")
        n = len(r.json().get("events", [])) if c == 200 else None
        print(lg, q, c, n, (r.text[:120] if r is not None and c != 200 else ""))
        if c == 200 and n:
            for e in r.json()["events"][:12]: print("   ", e["id"], e["date"], e["name"], e["status"]["type"]["name"])
c, r = get("https://site.api.espn.com/apis/site/v2/sports/soccer/caf.champions/scoreboard?dates=20261018")
if c == 200:
    evs = r.json().get("events", [])
    sa = [e for e in evs if "Sundowns" in e["name"] or "Pirates" in e["name"]] or evs[:1]
    for e in sa[:2]:
        c, s = get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/caf.champions/summary?event={e['id']}")
        j = s.json(); print(" SUMMARY", e["name"], c, sorted(j.keys()))
        print("  rosters", [(t.get("team",{}).get("displayName"), len(t.get("roster",[]))) for t in j.get("rosters", [])])
        if j.get("rosters"): print("  roster sample", json.dumps(j["rosters"][0].get("roster",[])[:2])[:700])
        print("  stats", json.dumps(j.get("boxscore",{}).get("teams",[{}])[0].get("statistics",[]))[:900])
        print("  keyEvents", [(k.get("clock",{}).get("displayValue"), k.get("type",{}).get("text"), k.get("text","")[:90]) for k in j.get("keyEvents",[])][:15])
        print("  commentary", len(j.get("commentary",[])))
print("===== CAF site links")
c, r = get("https://www.cafonline.com/")
if r is not None:
    links = sorted(set(re.findall(r'href="([^"]+)"', r.text)))
    print([l for l in links if re.search(r"champions|confed|match|fixture|result|centre|center", l, re.I)][:60])
    print("scripts", re.findall(r'<script[^>]+src="([^"]+)"', r.text)[:20])
