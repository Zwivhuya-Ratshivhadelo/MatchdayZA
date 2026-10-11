"""Writes the competition pages with their content already in the HTML (log, results, next
matches and the game on the pitch), so search engines and ad reviewers see real content, and
pages show something before the scripts run. app.js redraws the same markup with live data.

Pages:  /  (Betway Premiership), /motsepe-foundation-championship/, /mtn8/, /carling-knockout/,
        /nedbank-cup/, /abc.html, plus sitemap.xml.
Run:    python build.py
"""
import html
import re
from datetime import datetime, timedelta

from common import DATA, ROOT, load_json, now_sast, slugify

SITE = "https://matchdayza.co.za"
PAGES = {   # data slug -> (address, name)
    "betway-premiership": ("/", "Betway Premiership"),
    "national-first-division": ("/motsepe-foundation-championship/", "Motsepe Foundation Championship"),
    "mtn8": ("/mtn8/", "MTN8"),
    "carling-knockout": ("/carling-knockout/", "Carling Knockout"),
    "nedbank-cup": ("/nedbank-cup/", "Nedbank Cup"),
}
BIG_CLUBS = {"kaizer-chiefs", "orlando-pirates", "mamelodi-sundowns"}
RESULTS_SHOWN = 6
INFO_PAGES = ["about.html", "contact.html", "privacy.html"]


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def slug(s):
    return slugify(s or "")


# ---------- dates (SAST) ----------
def parse_date(m):
    d = m.get("date") or ""
    if not d:
        return None
    try:
        return datetime.fromisoformat(d if "T" in d else d + "T12:00:00+02:00")
    except ValueError:
        return None


def day_label(m, today):
    d = parse_date(m)
    if not d:
        return "Date to be confirmed"
    k = d.date()
    if k == today:
        return "Today"
    if k == today + timedelta(days=1):
        return "Tomorrow"
    if k == today - timedelta(days=1):
        return "Yesterday"
    return d.strftime("%a %-d %b")


def bar_date(m):
    d = parse_date(m)
    return f'<span class="wd">{d:%a} </span>{d:%d.%m.%Y}' if d else ""


def kickoff(m):
    d = m.get("date") or ""
    return d[11:16] if "T" in d else ""


def game_key(m):
    if m.get("match_id"):
        return f"id{m['match_id']}"
    return slug(f"{(m.get('date') or '')[:10]}-{m['home']}-{m['away']}")


# ---------- the same markup app.js draws ----------
def crest(name, size=None):
    st = f' style="--size:{size}px"' if size else ""
    return (f'<span class="crest"{st}><img src="logos/{slug(name)}.png" alt="" loading="lazy" decoding="async" '
            f'onerror="this.parentNode.remove()"></span>')


def match_card(m, today, pick=False, selected=False):
    live = m.get("status") == "LIVE"
    top = (f'<span class="pill-live">Live {esc(m.get("minute") or "")}</span>' if live
           else f"<span>{esc(day_label(m, today))}</span>")
    right = "" if live else (kickoff(m) or "TBC")

    def row(team, sc):
        return (f'<div class="mcard-row">{crest(team, 26)}<span class="code">{esc(team)}</span>'
                + (f'<span class="sc">{sc}</span>' if live else "") + "</div>")

    inner = (f'<div class="mcard-top">{top}<span>{esc(right)}</span></div>'
             f'{row(m["home"], m.get("home_score"))}{row(m["away"], m.get("away_score"))}')
    cls = f'mcard {"live" if live else ""} {"selected" if selected else ""}'
    if pick:
        return (f'<button type="button" class="{cls}" data-key="{esc(game_key(m))}" '
                f'aria-pressed="{"true" if selected else "false"}">{inner}</button>')
    return f'<div class="{cls}">{inner}</div>'


def result_card(m, extra=False, pick=False):
    def side(t):
        return f'<span class="lc-team"><b>{esc(t)}</b>{crest(t, 30)}</span>'

    def side_r(t):
        return f'<span class="lc-team">{crest(t, 30)}<b>{esc(t)}</b></span>'

    inner = (f'<div class="lc-bar"><span class="dt">{bar_date(m)}</span><span>FT</span></div>'
             f'<div class="lc-body">{side(m["home"])}<span class="lc-score">{m["home_score"]} - {m["away_score"]}</span>'
             f'{side_r(m["away"])}</div>')
    ex = " extra" if extra else ""
    if pick:
        return (f'<button type="button" class="lc{ex} pick" data-key="{esc(game_key(m))}">{inner}'
                f'<span class="lc-more">View match</span></button>')
    return f'<article class="lc{ex}">{inner}</article>'


def results_list(done, pick=False):
    if not done:
        return ""
    cards = "".join(result_card(m, i >= RESULTS_SHOWN, pick) for i, m in enumerate(done))
    more = '<button class="more-btn" type="button">Show all results</button>' if len(done) > RESULTS_SHOWN else ""
    return f'<div class="rcards">{cards}</div>{more}'


def pitch_svg():
    js = (ROOT / "app.js").read_text(encoding="utf-8")
    m = re.search(r"const PITCH_SVG = `(.*?)`;", js, re.S)
    return m.group(1) if m else ""


def pitch_card(m, comp_name, today, svg):
    played = m.get("status") in ("FT", "LIVE")
    live = m.get("status") == "LIVE"
    if played:
        centre = (f'{m["home_score"]} - {m["away_score"]}<small>'
                  f'{"Live " + esc(m.get("minute") or "") if live else "Full time"}</small>')
    else:
        centre = f'{kickoff(m) or "TBC"}<small>{esc(day_label(m, today))}</small>'
    latest = f'<div class="featured-latest">{esc(m["latest"])}</div>' if live and m.get("latest") else ""
    venue = f'<div class="featured-venue">{esc(m["venue"])}</div>' if m.get("venue") else ""
    return (f'<article class="featured">{svg}'
            f'<div class="featured-meta"><span class="featured-comp">{esc(comp_name)}</span></div>'
            f'<div class="featured-main">'
            f'<div class="featured-team">{crest(m["home"])}<strong>{esc(m["home"])}</strong></div>'
            f'<div class="featured-score">{centre}</div>'
            f'<div class="featured-team">{crest(m["away"])}<strong>{esc(m["away"])}</strong></div>'
            f'</div>{latest}{venue}</article>')


def enrich_log(log, results, extra=None):
    ids = {r.get("match_id") for r in results if r.get("match_id")}
    games = {}
    allm = list(results) + [e for e in (extra or []) if e.get("match_id") not in ids]
    for r in sorted(allm, key=lambda x: x.get("date") or ""):
        if r.get("status") != "FT":
            continue
        games.setdefault(slug(r["home"]), []).append((r["home_score"], r["away_score"]))
        games.setdefault(slug(r["away"]), []).append((r["away_score"], r["home_score"]))
    rows = []
    for row in log:
        g = games.get(slug(row["team"]), [])
        form = ["W" if f > a else "D" if f == a else "L" for f, a in g[-5:]]
        gd = row.get("gd")
        if gd is None and g and len(g) == row.get("p"):
            gd = sum(f - a for f, a in g)
        rows.append({**row, "form": form, "gd": gd})
    return rows


def standings_table(rows):
    def gd(v):
        return "–" if v is None else (f"+{v}" if v > 0 else str(v))

    body = "".join(
        f'<tr><td class="pos">{r["pos"]}</td><td class="club"><div>{crest(r["team"])}{esc(r["team"])}</div></td>'
        f'<td>{r["p"]}</td><td class="hide-sm">{r["w"]}</td><td class="hide-sm">{r["d"]}</td><td class="hide-sm">{r["l"]}</td>'
        f'<td>{gd(r["gd"])}</td><td class="pts">{r["pts"]}</td>'
        f'<td class="form hide-sm">{"".join(f"<span class={chr(34)}{f}{chr(34)}>{f}</span>" for f in r["form"])}</td></tr>'
        for r in rows)
    return ('<div class="table-wrap"><table class="standings"><thead><tr><th></th><th class="club">Club</th>'
            '<th title="Played">P</th><th class="hide-sm" title="Won">W</th><th class="hide-sm" title="Drawn">D</th>'
            '<th class="hide-sm" title="Lost">L</th><th title="Goal difference">GD</th><th title="Points">Pts</th>'
            f'<th class="hide-sm">Form</th></tr></thead><tbody>{body}</tbody></table></div>')


def nav(active):
    items = [(k, url, name) for k, (url, name) in PAGES.items()] + [("abc", "/abc.html", "ABC Motsepe League")]
    return "".join(f'<a href="{url}" data-k="{k}" data-page="1"{" aria-current=" + chr(34) + "page" + chr(34) if k == active else ""}>'
                   f"{esc(name)}</a>" for k, url, name in items)


def fill(template, values):
    out = template
    for k, v in values.items():
        out = out.replace("{{" + k + "}}", v)
    left = re.findall(r"\{\{\w+\}\}", out)
    if left:
        raise ValueError(f"template placeholders not filled: {left}")
    return out


# ---------- pages ----------
def build_comp(slug_, template, svg, today):
    url, name = PAGES[slug_]
    comp = load_json(DATA / "psl" / f"{slug_}.json", {}) or {}
    fixtures = sorted(comp.get("fixtures", []), key=lambda m: m.get("date") or "")
    results = comp.get("results", [])
    live = [m for m in results if m.get("status") == "LIVE"]
    done = sorted([m for m in results if m.get("status") == "FT"], key=lambda m: m.get("date") or "", reverse=True)

    big = next((m for m in fixtures if slug(m["home"]) in BIG_CLUBS or slug(m["away"]) in BIG_CLUBS), None)
    pick = (live[0] if live else None) or big or (fixtures[0] if fixtures else None) or (done[0] if done else None)
    pick_key = game_key(pick) if pick else None

    nxt = (live + fixtures)[:12]
    next_html = ("".join(match_card(m, today, True, game_key(m) == pick_key) for m in nxt) if nxt
                 else f'<p class="empty">No {esc(name)} matches scheduled yet.</p>')
    log = comp.get("log", [])

    league = " log," if comp.get("league") or log else ""
    title = (f"{name} log, fixtures and results | MatchdayZA" if league
             else f"{name} fixtures and results | MatchdayZA")
    if slug_ == "betway-premiership":
        title = "MatchdayZA | Betway Premiership live scores, log, fixtures and results"
    desc = f"{name} live scores,{league} fixtures and results. Follow every game with stats, key moments and line-ups."
    page = fill(template, {
        "title": esc(title), "description": esc(desc), "canonical": SITE + url, "comp": slug_,
        "h1": esc(f"{name} live scores,{league} fixtures and results"),
        "nav": nav(slug_), "next_title": "Live now" if live else "Next matches", "next": next_html,
        "featured": pitch_card(pick, name, today, svg) if pick else "",
        "results": results_list(done, pick=True) or f'<p class="empty">No {esc(name)} results yet.</p>',
        "standings": standings_table(enrich_log(log, results, comp.get("extra"))) if log else "",
        "log_hidden": "" if log else " hidden",
    })
    path = ROOT / url.strip("/") / "index.html" if url != "/" else ROOT / "index.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(page, encoding="utf-8")
    return url


def build_abc(template, today):
    index = load_json(DATA / "abc" / "streams.json", {}) or {}
    streams = [s for s in (load_json(DATA / "abc" / f"{x['stream_id']}.json", None) for x in index.get("streams", [])) if s]
    values = {"title": "ABC Motsepe League logs, fixtures and results | MatchdayZA",
              "description": "ABC Motsepe League logs, fixtures and results for every province and stream.",
              "canonical": SITE + "/abc.html", "nav": nav("abc"), "provinces": "", "streams": "",
              "stream_hidden": "", "next": "", "results": "", "standings": "", "log_hidden": " hidden"}
    if streams:
        provinces = sorted({s.get("province") or "Other" for s in streams})
        prov = provinces[0]
        cur = next(s for s in streams if (s.get("province") or "Other") == prov)
        in_prov = [s for s in streams if (s.get("province") or "Other") == prov]
        fixtures = sorted(cur.get("fixtures", []), key=lambda m: m.get("date") or "")[:12]
        done = sorted([m for m in cur.get("results", []) if m.get("status") == "FT"],
                      key=lambda m: m.get("date") or "", reverse=True)
        log = cur.get("log", [])
        values.update({
            "provinces": "".join(f'<option{" selected" if p == prov else ""}>{esc(p)}</option>' for p in provinces),
            "streams": "".join(f'<option value="{esc(s["stream_id"])}"{" selected" if s is cur else ""}>{esc(s["name"])}</option>'
                               for s in in_prov),
            "stream_hidden": " hidden" if len(in_prov) < 2 else "",
            "next": ("".join(match_card(m, today) for m in fixtures) if fixtures
                     else f'<p class="empty">No fixtures listed for {esc(cur["name"])} yet.</p>'),
            "results": results_list(done) or f'<p class="empty">No results for {esc(cur["name"])} yet.</p>',
            "standings": standings_table(enrich_log(log, cur.get("results", []))) if log else "",
            "log_hidden": "" if log else " hidden",
        })
    (ROOT / "abc.html").write_text(fill(template, {k: (v if k in ("nav", "next", "results", "standings", "provinces", "streams", "stream_hidden", "log_hidden", "canonical") else esc(v)) for k, v in values.items()}),
                                   encoding="utf-8")
    return "/abc.html"


def build_sitemap(urls):
    day = now_sast().date().isoformat()
    rows = "".join(f"  <url><loc>{SITE}{u}</loc><lastmod>{day}</lastmod></url>\n" for u in urls)
    rows += "".join(f"  <url><loc>{SITE}/{p}</loc></url>\n" for p in INFO_PAGES)
    (ROOT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
                                      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                      f"{rows}</urlset>\n", encoding="utf-8")


def run():
    today = now_sast().date()
    svg = pitch_svg()
    home_t = (ROOT / "templates" / "home.html").read_text(encoding="utf-8")
    abc_t = (ROOT / "templates" / "abc.html").read_text(encoding="utf-8")
    urls = [build_comp(s, home_t, svg, today) for s in PAGES]
    urls.append(build_abc(abc_t, today))
    build_sitemap(urls)
    print("Built pages:", ", ".join(urls))


if __name__ == "__main__":
    run()
