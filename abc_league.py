"""Scrape the ABC Motsepe League (all provinces and streams) from the public league pages
and store it as JSON in data/abc/.

Run:  python abc_league.py
"""
import re
import sys

from bs4 import BeautifulSoup

from common import (DATA, clean, fetch, load_json, match_key, merge_matches, now_sast,
                    parse_date, save_json, slugify)

BASE = "https://inqaku.com"
PROVINCES_URL = f"{BASE}/leagues/provinces/view?league_type=ABC%20Motsepe"
PROVINCES = ["Eastern Cape", "Free State", "Gauteng", "KwaZulu Natal", "KwaZulu-Natal",
             "Limpopo", "Mpumalanga", "North West", "Northern Cape", "Western Cape"]

STREAM_RE = re.compile(r"season_id=(\d+)&(?:amp;)?stream_id=(\d+)")
DAY_RE = re.compile(r"^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*,?\s+(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})$")
NO_RE = re.compile(r"^#\s*(\d+)$")
TAIL_RE = re.compile(r"^[\s\d:\-–VSvs]+$")
TIME_RE = re.compile(r"\b(\d{1,2}:\d{2})\b")


def discover_streams(html):
    """Find every ABC Motsepe stream link and the province heading above it."""
    soup = BeautifulSoup(html, "html.parser")
    streams, seen = [], set()
    for a in soup.find_all("a", href=True):
        m = STREAM_RE.search(a["href"])
        name = clean(a.get_text())
        if not m or not name or m.group(2) in seen:
            continue
        province = None
        for h in a.find_all_previous(["h1", "h2", "h3", "h4", "h5", "h6", "strong", "b"]):
            t = clean(h.get_text())
            if t in PROVINCES:
                province = t.replace("KwaZulu-Natal", "KwaZulu Natal")
                break
        seen.add(m.group(2))
        short = re.sub(r"^ABC Motsepe League\s*[-–]\s*", "", name)
        streams.append({"season_id": m.group(1), "stream_id": m.group(2), "province": province,
                        "name": short, "slug": slugify(short)})
    return streams


def parse_log(html):
    soup = BeautifulSoup(html, "html.parser")
    rows, seen = [], set()
    for a in soup.find_all("a", href=True):
        if "team/view" not in a["href"] or not clean(a.get_text()):
            continue
        tr = a.find_parent("tr")
        team = clean(a.get_text())
        if not tr or team in seen:
            continue
        nums = [int(t) for t in (clean(c.get_text()) for c in tr.find_all(["td", "th"]))
                if re.fullmatch(r"[+-]?\d+", t)]
        if len(nums) < 8:
            continue
        p, w, d, l, gf, ga, gd, pts = nums[-8:]
        pos = nums[0] if len(nums) >= 9 else len(rows) + 1
        seen.add(team)
        rows.append({"pos": pos, "team": team, "p": p, "w": w, "d": d, "l": l,
                     "gf": gf, "ga": ga, "gd": gd, "pts": pts})
    rows.sort(key=lambda r: r["pos"])
    return rows


def parse_matches(html, stream_id):
    """Results/fixtures lists: date headings, then '<home> #N <away> - 3 0' or '- VS - 16:00'."""
    soup = BeautifulSoup(html, "html.parser")
    # the site writes spaces as "&nbsp" without the semicolon, which shows up as text
    text = soup.get_text("\n").replace("&nbsp;", " ").replace("&nbsp", " ")
    lines = [clean(t) for t in text.split("\n") if clean(t)]
    results, fixtures, day = [], [], None
    for i, line in enumerate(lines):
        d = DAY_RE.match(line)
        if d:
            day = (d.group(1), d.group(2), d.group(3))
            continue
        n = NO_RE.match(line)
        if not n or not day or i == 0 or i + 1 >= len(lines):
            continue
        home, away = lines[i - 1], lines[i + 1]
        tail = []
        for t in lines[i + 2:i + 8]:
            if not TAIL_RE.match(t) or NO_RE.match(t):
                break
            tail.append(t)
        tail_text = " ".join(tail)
        hhmm = TIME_RE.search(tail_text)
        no = n.group(1)
        m = {"home": home, "away": away, "match_no": int(no),
             "url": f"{BASE}/match/view?stream_id={stream_id}&match_no={no}&s=l"}
        # A score means it was played, even if the page also carries a hidden "VS"
        scores = re.findall(r"\b(\d{1,2})\b", TIME_RE.sub(" ", tail_text))
        if len(scores) >= 2:
            m.update(date=parse_date(*day), home_score=int(scores[0]),
                     away_score=int(scores[1]), status="FT")
            results.append(m)
        elif re.search(r"\bvs\b", tail_text, re.I):
            m.update(date=parse_date(*day, hhmm.group(1) if hhmm else None), status="NS")
            fixtures.append(m)
    return results, fixtures


def run():
    problems = []
    try:
        streams = discover_streams(fetch(PROVINCES_URL))
    except Exception as e:
        print(f"Could not load stream list: {e}")
        sys.exit(1)
    if not streams:  # fall back to the last known list rather than wiping data
        streams = load_json(DATA / "abc" / "streams.json", {}).get("streams", [])
        problems.append("no streams found on provinces page (layout changed?)")
    print(f"ABC Motsepe: {len(streams)} streams")
    today = now_sast().date().isoformat()

    for s in streams:
        q = f"season_id={s['season_id']}&stream_id={s['stream_id']}"
        path = DATA / "abc" / f"{s['stream_id']}.json"
        old = load_json(path, {})
        try:
            log = parse_log(fetch(f"{BASE}/leagues/view/?{q}"))
            res_html = fetch(f"{BASE}/league?{q}&tab=results")
            res, _ = parse_matches(res_html, s["stream_id"])
            if not res and s is streams[0]:  # keep a copy to diagnose an empty results page
                (DATA / "abc" / "_results_page_sample.html").write_text(res_html, encoding="utf-8")
            _, fix = parse_matches(fetch(f"{BASE}/league?{q}&tab=fixtures"), s["stream_id"])
        except Exception as e:
            problems.append(f"{s['name']}: {e}")
            continue
        if not log and not res and not fix:
            problems.append(f"{s['name']}: nothing parsed")
        results = merge_matches(old.get("results"), res)
        done = {match_key(r) for r in results}
        fixtures = [f for f in merge_matches(old.get("fixtures"), fix)
                    if match_key(f) not in done and (f.get("date") or "")[:10] >= today]
        save_json(path, {**s, "source": f"{BASE}/leagues/view/?{q}",
                         "updated": now_sast().isoformat(timespec="seconds"),
                         "log": log or old.get("log", []), "results": results, "fixtures": fixtures})
        print(f"  {s['province']} / {s['name']}: {len(log)} teams, {len(res)} results, {len(fix)} fixtures")

    save_json(DATA / "abc" / "streams.json",
              {"updated": now_sast().isoformat(timespec="seconds"), "streams": streams})
    if problems:
        print("PROBLEMS:\n  " + "\n  ".join(problems))
        sys.exit(1)


if __name__ == "__main__":
    run()
