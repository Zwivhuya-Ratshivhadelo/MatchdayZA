import requests, re
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}
def get(u):
    try:
        r = requests.get(u, headers=H, timeout=30); return r.status_code, r.text
    except Exception as e: return 0, str(e)
c, t = get("https://www.cafonline.com/caf-champions-league/")
print("CL page", c, len(t))
print("links", sorted(set(l for l in re.findall(r'href="([^"]+)"', t) if re.search(r"match|fixture|result|centre|stand", l, re.I)))[:60])
print("data attrs", sorted(set(re.findall(r'data-[a-z-]+="[^"]{1,80}"', t)))[:80])
print("opta", re.findall(r'<opta-widget[^>]*>', t)[:10])
for js in ["/js/widget/competition-match-widget.es5.min.js?v=20260626001"]:
    c, s = get("https://www.cafonline.com" + js)
    print("JS", c, len(s)); print(" urls", sorted(set(re.findall(r'["\'](/?[a-zA-Z0-9_./-]*(?:api|Api|json|match|Match)[a-zA-Z0-9_./?=&{}-]*)["\']', s)))[:60])
    print(" abs", sorted(set(re.findall(r'https?://[^"\' ]+', s)))[:30])
