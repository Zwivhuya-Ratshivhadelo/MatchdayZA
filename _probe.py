import requests, re
from bs4 import BeautifulSoup
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
def get(u):
    try:
        r = requests.get(u, headers=H, timeout=30); return r.status_code, r.text
    except Exception as e: return 0, str(e)
def txt(h): return re.sub(r"\s+", " ", BeautifulSoup(h, "html.parser").get_text(" "))
c, t = get("https://diskizone.com/leagues/abc-motsepe-limpopo-stream-a-18")
abc = sorted(set(re.findall(r'(/leagues/abc-[a-z0-9-]+)', t))); print("ABC", abc)
for p in abc:
    c, t = get("https://diskizone.com" + p)
    x = txt(t); i = x.find("Share: Results")
    print("===", p, c, x[i:i+700])
for q in ["abc motsepe wrap", "motsepe league results"]:
    c, t = get("https://farpost.co.za/?s=" + q.replace(" ", "+"))
    print("=== farpost search", q, c, list(dict.fromkeys(re.findall(r'https://(?:www\.)?farpost\.co\.za/2026/[0-9/]+[a-z0-9-]+/?', t)))[:15])
