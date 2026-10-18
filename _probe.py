import requests, re, json
from bs4 import BeautifulSoup
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
def get(u, **k):
    try:
        r = requests.get(u, headers=H, timeout=25, **k); return r.status_code, r.text
    except Exception as e: return 0, str(e)
def txt(h): return re.sub(r"\s+", " ", BeautifulSoup(h, "html.parser").get_text(" "))
print("=== 365 search")
for q in ["motsepe", "abc motsepe", "second division south africa", "safa"]:
    c, t = get(f"https://webws.365scores.com/web/search/?appTypeId=5&langId=1&query={q}")
    print(q, c, t[:800])
print("=== 365 SA comps")
c, t = get("https://webws.365scores.com/web/competitions/?appTypeId=5&langId=1&sports=1&countries=150")
try:
    for x in json.loads(t).get("competitions", []): print(x.get("id"), x.get("name"), x.get("countryId"))
except Exception as e: print(c, t[:300])
print("=== sofascore")
for u in ["https://api.sofascore.com/api/v1/search/all?q=motsepe", "https://api.sofascore.com/api/v1/search/unique-tournaments?q=motsepe"]:
    c, t = get(u); print(u, c, t[:800])
print("=== inqaku match 28322/13")
c, t = get("https://inqaku.com/match/view?stream_id=28322&match_no=13&s=l"); print(c, txt(t)[:2500])
print("=== inqaku results tab LP A")
c, t = get("https://inqaku.com/league?season_id=17737&stream_id=28322&tab=results"); print(c, txt(t)[:1500])
print("=== inqaku fixtures tab LP A")
c, t = get("https://inqaku.com/league?season_id=17737&stream_id=28322&tab=fixtures"); print(c, txt(t)[:1500])
print("=== safa")
for u in ["https://www.safa.net/", "https://www.safa.net/abc-motsepe-league/"]:
    c, t = get(u); print(u, c, txt(t)[:600])
print("=== flashscore")
c, t = get("https://www.flashscore.com/football/south-africa/"); print(c, re.findall(r'/football/south-africa/[a-z0-9-]+/', t)[:60])
