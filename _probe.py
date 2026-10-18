import requests, re
from bs4 import BeautifulSoup
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
def get(u):
    try:
        r = requests.get(u, headers=H, timeout=25); return r.status_code, r.text
    except Exception as e: return 0, str(e)
def txt(h): return re.sub(r"\s+", " ", BeautifulSoup(h, "html.parser").get_text(" "))
for u in ["https://safa.ptsportsuite.com/competitions/abc-motsepe-league/", "https://safa.ptsportsuite.com/"]:
    c, t = get(u); print("===", u, c, len(t)); print(txt(t)[:3000])
    print("LINKS", sorted(set(re.findall(r'href="([^"]+)"', t)))[:150])
    print("SCRIPTS", re.findall(r'(?:src|data-[a-z-]+)="([^"]*(?:api|json|ajax|widget)[^"]*)"', t)[:40])
    print("APIHINTS", sorted(set(re.findall(r'https?://[a-z0-9.-]+/[^"\' ]*(?:api|json)[^"\' ]*', t)))[:40])
for p in ["Limpopo", "Free_State", "Northern_Cape", "Mpumalanga"]:
    c, t = get(f"https://en.wikipedia.org/w/index.php?title=2026%E2%80%9327_SAFA_Second_Division_{p}&action=raw")
    print("=== wiki", p, c, len(t)); print(t[:2500])
