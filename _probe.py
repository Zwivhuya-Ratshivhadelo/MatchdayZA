import requests, json
import caf
s = caf.get("standings/?competitions=624&seasonNum=66")
r = s["standings"][0]["rows"][0]; print("ROW KEYS", sorted(k for k in r if k != "competitor")); print({k: v for k, v in r.items() if k != "competitor"})
orig = caf.get
caf.get = lambda p: orig(p + "&seasonNum=66" if p.startswith("standings") else p)
for g in caf.groups(624)[:2]: print(g["name"], g["log"][:2])
