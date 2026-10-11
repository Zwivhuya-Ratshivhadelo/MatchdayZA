"""Download PSL club logos (Betway Premiership and Motsepe Foundation Championship) from psl.co.za
into logos/<club-name>.png, named the way the site expects them.

Run:  python logos.py            (skips logos you already have)
      python logos.py --refresh  (downloads them all again)
"""
import re
import sys
from urllib.parse import quote, unquote, urljoin

from bs4 import BeautifulSoup

from common import ROOT, _session, fetch, slugify

BASE = "https://www.psl.co.za"
PAGES = [f"{BASE}/", f"{BASE}/tournament/betway-premiership", f"{BASE}/tournament/national-first-division"]
LOGO_RE = re.compile(r"/psl/clublogos/(?:small/)?([^/?#]+)\.(png|jpg|jpeg|webp)", re.I)
OUT = ROOT / "logos"


def find_logos():
    """Map club slug -> best logo URL (full-size version rather than the small one)."""
    found = {}
    for page in PAGES:
        try:
            soup = BeautifulSoup(fetch(page), "html.parser")
        except Exception as e:
            print(f"  could not load {page}: {e}")
            continue
        for img in soup.find_all("img", src=True):
            src = urljoin(page, img["src"])
            m = LOGO_RE.search(src)
            if not m:
                continue
            name = unquote(m.group(1))
            big = src.replace("/clublogos/small/", "/clublogos/")
            found.setdefault(slugify(name), (name, big))
    return found


def download(url):
    # spaces in file names ("AmaZulu FC.png") need encoding
    head, tail = url.rsplit("/", 1)
    r = _session.get(f"{head}/{quote(unquote(tail))}", timeout=30)
    r.raise_for_status()
    if not r.headers.get("content-type", "").startswith("image") or len(r.content) < 200:
        raise ValueError("not an image")
    return r.content


def run(refresh=False):
    OUT.mkdir(exist_ok=True)
    logos = find_logos()
    print(f"Found {len(logos)} club logos")
    saved = 0
    for slug, (name, url) in sorted(logos.items()):
        path = OUT / f"{slug}.png"
        if path.exists() and not refresh:
            continue
        try:
            data = download(url)
        except Exception:
            try:  # fall back to the small version if the full-size one isn't there
                data = download(url.replace("/clublogos/", "/clublogos/small/"))
            except Exception as e:
                print(f"  {name}: failed ({e})")
                continue
        path.write_bytes(data)
        saved += 1
        print(f"  saved logos/{slug}.png  ({name})")
    print(f"Done: {saved} new logo files")
    if not logos:
        sys.exit(1)


if __name__ == "__main__":
    run(refresh="--refresh" in sys.argv)
