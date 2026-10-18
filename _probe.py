import requests, re
from bs4 import BeautifulSoup
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
def get(u):
    try:
        r = requests.get(u, headers=H, timeout=25); return r.status_code, r.text
    except Exception as e: return 0, str(e)
def txt(h): return re.sub(r"\s+", " ", BeautifulSoup(h, "html.parser").get_text(" "))
c, t = get("https://farpost.co.za/south-african-football/abc-motsepe-league/")
links = list(dict.fromkeys(re.findall(r'https://(?:www\.)?farpost\.co\.za/20\d\d/\d\d/\d\d/[a-z0-9-]+/?', t)))
print("=== farpost category", c); [print(l) for l in links[:25]]
wraps = [l for l in links if "wrap" in l or "results" in l][:2]
for w in wraps:
    c, t = get(w); s = BeautifulSoup(t, "html.parser"); a = s.find("article") or s
    print("=== WRAP", w, c); print(re.sub(r"\s+", " ", a.get_text("\n"))[:5000])
c, t = get("https://en.wikipedia.org/w/index.php?title=2026%E2%80%9327_SAFA_Second_Division&action=raw")
print("=== wiki 26-27", c, t[:3000])
