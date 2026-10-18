import requests, re
from bs4 import BeautifulSoup
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
def get(u):
    try:
        r = requests.get(u, headers=H, timeout=30); return r.status_code, r.text
    except Exception as e: return 0, str(e)
def txt(h): return re.sub(r"\s+", " ", BeautifulSoup(h, "html.parser").get_text(" "))
c, t = get("https://diskizone.com/leagues/abc-motsepe-limpopo-stream-a-18")
print("=== dz LP A", c, len(t)); print(txt(t)[:6000])
print("LINKS", sorted(set(re.findall(r'href="([^"]+)"', t)))[:200])
print("API", sorted(set(re.findall(r'["\'](https?://[^"\']*(?:api|json|ajax)[^"\']*)', t)))[:40])
print("SCRIPTS", re.findall(r'<script[^>]+src="([^"]+)"', t)[:30])
c, t = get("https://diskizone.com/leagues"); print("=== dz leagues", c); print(sorted(set(re.findall(r'href="(/leagues/[^"]+)"', t)))[:120])
for u in ["https://safa.ptsportsuite.com/competitions/abc-motsepe-league/"]:
    try:
        r = requests.get(u, headers=H, timeout=60); print("=== pts", r.status_code, txt(r.text)[:1500])
    except Exception as e: print("=== pts", e)
