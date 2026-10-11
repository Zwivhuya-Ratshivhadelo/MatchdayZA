"""Shared helpers: polite HTTP fetching, JSON storage, dates, slugs."""
import json
import os
import re
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
SAST = timezone(timedelta(hours=2))  # South Africa has no daylight saving

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept-Language": "en-ZA,en;q=0.9",
}
_session = requests.Session()
_session.headers.update(HEADERS)
_last_request = 0.0
REQUEST_GAP = float(os.environ.get("REQUEST_GAP", "2.0"))  # seconds between requests


def fetch(url, retries=3):
    """GET a page with a gap between requests and simple retries. Returns HTML text."""
    global _last_request
    for attempt in range(1, retries + 1):
        wait = REQUEST_GAP - (time.time() - _last_request)
        if wait > 0:
            time.sleep(wait)
        _last_request = time.time()
        try:
            r = _session.get(url, timeout=30)
            r.raise_for_status()
            r.encoding = r.encoding or "utf-8"
            if os.environ.get("SAVE_HTML"):  # debug: keep raw pages to fix parsers
                snap = DATA / "_debug"
                snap.mkdir(parents=True, exist_ok=True)
                (snap / (slugify(url)[:120] + ".html")).write_text(r.text, encoding="utf-8")
            return r.text
        except requests.RequestException as e:
            print(f"  fetch failed ({attempt}/{retries}) {url}: {e}")
            if attempt == retries:
                raise
            time.sleep(5 * attempt)


def now_sast():
    return datetime.now(SAST)


def slugify(text):
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def parse_date(day, mon, year=None, hhmm=None, ref=None):
    """Build an ISO date/datetime string. If year is missing, pick the year that puts
    the date closest to `ref` (fixtures near a new year roll over correctly)."""
    month = MONTHS.get(mon[:3].lower())
    if not month:
        return None
    day = int(day)
    ref = ref or now_sast()
    if year:
        year = int(year)
    else:
        candidates = [ref.year - 1, ref.year, ref.year + 1]
        year = min(candidates, key=lambda y: abs(
            (datetime(y, month, min(day, 28), tzinfo=SAST) - ref).days))
    if hhmm:
        h, m = hhmm.split(":")
        return datetime(year, month, day, int(h), int(m), tzinfo=SAST).isoformat()
    return f"{year:04d}-{month:02d}-{day:02d}"


def load_json(path, default=None):
    path = Path(path)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def save_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def match_key(m):
    """Stable key for a match: date + teams (survives re-scrapes)."""
    return f"{(m.get('date') or '')[:10]}|{slugify(m['home'])}|{slugify(m['away'])}"


def merge_matches(old, new):
    """Merge freshly scraped matches into stored ones (new data wins, history is kept)."""
    merged = {match_key(m): m for m in old or []}
    for m in new:
        k = match_key(m)
        merged[k] = {**merged.get(k, {}), **{a: b for a, b in m.items() if b not in (None, "")}}
    return sorted(merged.values(), key=lambda m: m.get("date") or "")


def score_line(m):
    return f"{m['home']} {m['home_score']}–{m['away_score']} {m['away']}"
