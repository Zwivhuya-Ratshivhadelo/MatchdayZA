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

from common import DATA, ROOT, load_json, now_sast, save_json, slugify

SITE = "https://www.matchdayza.co.za"
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
    if pick:   # tapping it puts the game on the pitch
        return (f'<button type="button" class="{cls}" data-key="{esc(game_key(m))}" '
                f'aria-pressed="{"true" if selected else "false"}">{inner}</button>')
    return f'<div class="{cls}">{inner}</div>'


CLUBS = set()   # clubs with their own page (every club in a PSL league log)


def club_url(name):
    return f"/{slug(name)}/"


def match_url(m):
    return f"/match/{slug(m['home'])}-vs-{slug(m['away'])}-{m['date'][:10]}/" if m.get("date") else None


def team_link(team):
    return f'<a href="{club_url(team)}">{esc(team)}</a>' if slug(team) in CLUBS else esc(team)


def result_card(m, extra=False, pick=False, label="", link=False):
    def side(t):
        return f'<span class="lc-team"><b>{esc(t)}</b>{crest(t, 30)}</span>'

    def side_r(t):
        return f'<span class="lc-team">{crest(t, 30)}<b>{esc(t)}</b></span>'

    inner = (f'<div class="lc-bar"><span class="dt">{bar_date(m)}</span><span>FT</span></div>'
             f'<div class="lc-body">{side(m["home"])}<span class="lc-score">{m["home_score"]} - {m["away_score"]}</span>'
             f'{side_r(m["away"])}</div>'
             + (f'<div class="lc-scorers">{scorers_html(m, 0, "h") or "<span></span>"}{scorers_html(m, 1, "a") or "<span></span>"}</div>'
                if SCORERS.get(str(m.get("match_id"))) else "")
             + (f'<div class="lc-comp">{esc(label)}</div>' if label else ""))
    ex = " extra" if extra else ""
    url = match_url(m) if (link or pick) else None   # the card opens the game's own page
    if url:
        return f'<a href="{url}" class="lc{ex}">{inner}<span class="lc-more">View match</span></a>'
    return f'<article class="lc{ex}">{inner}</article>'


def results_list(done, pick=False, label_of=None, link=False):
    if not done:
        return ""
    cards = "".join(result_card(m, i >= RESULTS_SHOWN, pick, label_of(m) if label_of else "", link) for i, m in enumerate(done))
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
            f'<div class="featured-team">{crest(m["home"])}<strong>{team_link(m["home"])}</strong>{scorers_html(m, 0, "scorers") if played else ""}</div>'
            f'<div class="featured-score">{centre}</div>'
            f'<div class="featured-team">{crest(m["away"])}<strong>{team_link(m["away"])}</strong>{scorers_html(m, 1, "scorers") if played else ""}</div>'
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


def standings_table(rows, links=False, highlight=None):
    def gd(v):
        return "–" if v is None else (f"+{v}" if v > 0 else str(v))

    body = "".join(
        f'<tr{" class=" + chr(34) + "me" + chr(34) if highlight and slug(highlight) == slug(r["team"]) else ""}>'
        f'<td class="pos">{r["pos"]}</td><td class="club"><div>{crest(r["team"])}{team_link(r["team"]) if links else esc(r["team"])}</div></td>'
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

    done = [m for m in done if game_key(m) != pick_key]   # the game on the pitch is not repeated
    nxt = (live + fixtures)[:12]
    next_html = ("".join(match_card(m, today, True, game_key(m) == pick_key) for m in nxt) if nxt
                 else f'<p class="empty">No {esc(name)} matches scheduled yet.</p>')
    log = comp.get("log", [])

    league = " log," if comp.get("league") or log else ""
    title = (f"{name} log, fixtures and results | MatchdayZA" if league
             else f"{name} fixtures and results | MatchdayZA")
    if slug_ == "betway-premiership":
        title = "MatchdayZA | Betway Premiership live scores, log, fixtures and results"
    desc = f"{name} live scores,{league} fixtures and results. Follow every game with stats, commentary and line-ups."
    page = fill(template, {
        "title": esc(title), "description": esc(desc), "canonical": SITE + url, "comp": slug_,
        "h1": esc(f"{name} live scores,{league} fixtures and results"),
        "nav": nav(slug_), "next_title": "Live now" if live else "Next matches", "next": next_html,
        "featured": pitch_card(pick, name, today, svg) if pick else "",
        "results": results_list(done, pick=True, link=True) or f'<p class="empty">No {esc(name)} results yet.</p>',
        "standings": standings_table(enrich_log(log, results, comp.get("extra")), links=True) if log else "",
        "log_hidden": "" if log else " hidden",
    })
    write(url, page)
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


def write(url, page):
    """Write a page at its address, only when it changed (keeps commits small)."""
    path = ROOT / url.strip("/") / "index.html" if url != "/" else ROOT / "index.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text(encoding="utf-8") != page:
        path.write_text(page, encoding="utf-8")


# ---------- stats, commentary and line-ups (same as app.js detailPanel) ----------
def _who(e):
    return f"{e.get('player')} ({e.get('team')})" if e.get("player") else f"{e.get('team')}"


EVENT_TEXT = {   # without a player's name (some sources only give the club) the line names the club
    "goal": lambda e: f"Goal! {_who(e)}" if e.get("player") else f"Goal, {e.get('team')}",
    "penalty_goal": lambda e: f"Penalty scored by {_who(e)}" if e.get("player") else f"Penalty scored, {e.get('team')}",
    "own_goal": lambda e: f"Own goal by {_who(e)}" if e.get("player") else f"Own goal, {e.get('team')}",
    "penalty_saved": lambda e: f"Penalty saved, {_who(e)} denied",
    "penalty_missed": lambda e: f"Penalty missed by {_who(e)}" if e.get("player") else f"Penalty missed, {e.get('team')}",
    "penalty_won": lambda e: f"Penalty to {e.get('team')}, {e.get('player')} fouled" if e.get("player") else f"Penalty to {e.get('team')}",
    "yellow": lambda e: f"Yellow card, {_who(e)}",
    "second_yellow": lambda e: f"Second yellow, {_who(e)} sent off",
    "red": lambda e: f"Red card, {_who(e)}",
    "sub": lambda e: f"{e.get('team')}: {e.get('player_in')} on, {e.get('player_out')} off",
    "var": lambda e: "VAR check",
}
PERIOD_TEXT = {"kickoff": "Kick-off", "half_time": "Half-time", "second_half": "Second half", "full_time": "Full time",
               "extra_time": "Extra time", "shootout": "Penalty shootout"}
ICON = {
    "goal": '<span class="ev-ico goal">⚽</span>', "penalty_goal": '<span class="ev-ico goal">⚽</span>',
    "own_goal": '<span class="ev-ico goal og">⚽</span>', "yellow": '<span class="ev-ico card y"></span>',
    "red": '<span class="ev-ico card r"></span>', "second_yellow": '<span class="ev-ico card yr"></span>',
    "sub": '<span class="ev-ico sub">⇄</span>', "penalty_saved": '<span class="ev-ico miss">✕</span>',
    "penalty_missed": '<span class="ev-ico miss">✕</span>', "penalty_won": '<span class="ev-ico pen">P</span>',
    "var": '<span class="ev-ico var">VAR</span>',
}


def detail_panel(detail):
    if not detail:
        return ""
    parts = []
    stats = detail.get("stats") or []
    if stats:
        rows = ""
        for st in stats:
            try:
                h = float(str(st["home"]).rstrip("%")) or 0
            except ValueError:
                h = 0
            try:
                a = float(str(st["away"]).rstrip("%")) or 0
            except ValueError:
                a = 0
            tot = (h + a) or 1
            rows += (f'<div class="stat"><div class="stat-row"><b>{esc(st["home"])}</b><span>{esc(st["label"])}</span><b>{esc(st["away"])}</b></div>'
                     f'<div class="stat-bar"><i class="h" style="width:{h / tot * 100:g}%"></i><i class="a" style="width:{a / tot * 100:g}%"></i></div></div>')
        parts.append(f'<section class="panel"><div class="panel-head"><h2>Stats</h2></div>{rows}</section>')
    events = detail.get("events") or []
    # commentary only when the source had real commentary (named players or match periods), not just goal times
    if any(e.get("player") or e.get("player_in") or e.get("type") in PERIOD_TEXT for e in events):
        items = ""
        for e in events:
            t = e.get("type")
            if t in PERIOD_TEXT:
                items += f'<li class="ev-period"><span>{PERIOD_TEXT[t]}</span></li>'
                continue
            text = EVENT_TEXT.get(t, lambda e: "")(e)
            score = f'<b class="ev-score">{e["score"][0]} - {e["score"][1]}</b>' if e.get("score") else ""
            items += (f'<li class="ev ev-{esc(t)}"><span class="ev-min">{esc(e.get("minute"))}</span>{ICON.get(t, "")}'
                      f'<span class="ev-text">{esc(text)}</span>{score}</li>')
        parts.append(f'<section class="panel"><div class="panel-head"><h2>Commentary</h2></div><ol class="timeline">{items}</ol></section>')
    lineups = detail.get("lineups") or []
    if lineups:
        def lst(ps):
            return "".join(f'<li><span class="lu-no">{esc(p.get("no"))}</span><span class="lu-name">{esc(p.get("name"))}</span>'
                           f'<span class="lu-pos">{esc(p.get("pos"))}</span></li>' for p in ps)
        teams = "".join(
            f'<div class="lu-team"><h3>{crest(t["team"], 24)}{esc(t["team"])}</h3><h4>Starting XI</h4><ol class="lu-list">{lst(t["starting"])}</ol>'
            + (f'<h4>Substitutes</h4><ol class="lu-list">{lst(t["subs"])}</ol>' if t.get("subs") else "") + "</div>"
            for t in lineups)
        parts.append(f'<section class="panel"><div class="panel-head"><h2>Line-ups</h2></div><div class="lineups">{teams}</div></section>')
    return "".join(parts)


# ---------- goal scorers (under each club, like score sites do) ----------
GOAL_TYPES = ("goal", "penalty_goal", "own_goal")


def scorer_lists(detail, home, away):
    """[home scorers, away scorers] as short lines, e.g. "Mokoena 11', 67'" or "50'" when no name is known."""
    goals = [e for e in (detail or {}).get("events", []) if e.get("type") in GOAL_TYPES]
    goals.reverse()   # events are stored newest first
    sides = ([], [])
    prev = [0, 0]
    for e in goals:
        sc = e.get("score")
        if sc and len(sc) == 2 and (sc[0] != prev[0] or sc[1] != prev[1]):
            side = 0 if sc[0] > prev[0] else 1
            prev = list(sc)
        else:   # no running score: go by the club (an own goal counts for the other side)
            own = slug(e.get("team")) in (slug(home), slug(away))
            side = 0 if slug(e.get("team")) == slug(home) else 1
            if e["type"] == "own_goal" and own:
                side = 1 - side
        name = (e.get("player") or "").split()[-1] if e.get("player") else ""
        tag = " (pen)" if e["type"] == "penalty_goal" else " (og)" if e["type"] == "own_goal" else ""
        sides[side].append((name, f"{e.get('minute', '')}{tag}"))
    out = []
    for lst in sides:
        lines, order = {}, []
        for name, minute in lst:
            if name not in lines:
                lines[name] = []
                order.append(name)
            lines[name].append(minute)
        out.append([f"{n} {', '.join(lines[n])}".strip() for n in order])
    return out


def build_scorers(comps):
    """data/psl/scorers.json: match number -> [home scorers, away scorers], read by app.js."""
    out = {}
    for c in comps.values():
        for m in c.get("results", []):
            if not m.get("match_id"):
                continue
            d = load_json(DATA / "psl" / "matches" / f"{m['match_id']}.json", None)
            lists = scorer_lists(d, m["home"], m["away"]) if d else [[], []]
            if lists[0] or lists[1]:
                out[str(m["match_id"])] = lists
    path = DATA / "psl" / "scorers.json"
    if load_json(path, None) != out:
        save_json(path, out)
    return out


SCORERS = {}


def scorers_html(m, side, cls):
    lst = SCORERS.get(str(m.get("match_id")), [[], []])[side] if m.get("match_id") else []
    return f'<span class="{cls}">' + "".join(f"<span>{esc(x)}</span>" for x in lst) + "</span>" if lst else ""


def merge_detail(m, detail):
    if detail and detail.get("status") != "NS":
        return {**m, "home_score": detail.get("home_score"), "away_score": detail.get("away_score"),
                "status": detail.get("status"), "minute": detail.get("minute") or m.get("minute")}
    return dict(m)


# ---------- club and match pages ----------
def load_comps():
    return {k: load_json(DATA / "psl" / f"{k}.json", {}) or {} for k in PAGES}


def build_club(club, comps, template, svg, today):
    s = slug(club)
    fixtures, results = [], []
    for k, comp in comps.items():
        fixtures += [{**m, "_comp": k} for m in comp.get("fixtures", []) if s in (slug(m["home"]), slug(m["away"]))]
        results += [{**m, "_comp": k} for m in comp.get("results", []) if s in (slug(m["home"]), slug(m["away"]))]
    fixtures.sort(key=lambda m: m.get("date") or "")
    live = [m for m in results if m.get("status") == "LIVE"]
    done = sorted([m for m in results if m.get("status") == "FT"], key=lambda m: m.get("date") or "", reverse=True)
    pick = (live[0] if live else None) or (fixtures[0] if fixtures else None) or (done[0] if done else None)
    pick_key = game_key(pick) if pick else None
    done = [m for m in done if game_key(m) != pick_key]   # the game on the pitch is not repeated
    nxt = (live + fixtures)[:12]
    league = next((k for k, c in comps.items() if any(slug(r["team"]) == s for r in c.get("log", []))), None)
    lc = comps.get(league, {}) if league else {}
    name_of = lambda m: PAGES[m["_comp"]][1]
    page = fill(template, {
        "title": esc(f"{club} fixtures, results and log | MatchdayZA"),
        "description": esc(f"{club} live scores, fixtures, results and log position"
                           + (f" in the {PAGES[league][1]}" if league else "") + ", with stats and line-ups for every game."),
        "canonical": SITE + club_url(club), "club_name": esc(club), "club_crest": crest(club),
        "nav": nav(None), "next_title": "Live now" if live else "Next matches",
        "next": ("".join(match_card(m, today, True, game_key(m) == pick_key) for m in nxt) if nxt
                 else f'<p class="empty">No {esc(club)} matches scheduled yet.</p>'),
        "featured": pitch_card(pick, name_of(pick), today, svg) if pick else "",
        "results": results_list(done, True, name_of, True) or f'<p class="empty">No {esc(club)} results yet.</p>',
        "standings": standings_table(enrich_log(lc.get("log", []), lc.get("results", []), lc.get("extra")), True, club) if league else "",
        "log_hidden": "" if league else " hidden",
    })
    write(club_url(club), page)
    return club_url(club)


def build_match(m, comp_key, comps, template, svg, today):
    url = match_url(m)
    comp = comps[comp_key]
    comp_name = PAGES[comp_key][1]
    detail = load_json(DATA / "psl" / "matches" / f"{m['match_id']}.json", None) if m.get("match_id") else None
    g = merge_detail(m, detail)
    d = parse_date(g)
    when = f"{d:%-d %B %Y}" if d else ""
    if g.get("status") == "LIVE":
        head = f'{g["home"]} {g["home_score"]}-{g["away_score"]} {g["away"]} Live Score'
        desc = f'{head}, {comp_name}. Commentary, stats and line-ups as it happens.'
    elif g.get("status") == "FT":
        head = f'{g["home"]} {g["home_score"]}-{g["away_score"]} {g["away"]}'
        desc = f'{g["home"]} {g["home_score"]}-{g["away_score"]} {g["away"]}, {comp_name}, {when}. Stats, commentary and line-ups.'
    else:
        head = f'{g["home"]} vs {g["away"]} Live Score'
        desc = (f'{g["home"]} vs {g["away"]}, {comp_name}, {when}' + (f' at {kickoff(g)}' if kickoff(g) else "")
                + '. Live score, stats, commentary and line-ups.')
    page = fill(template, {
        "title": esc(f"{head} | {comp_name} | MatchdayZA"), "description": esc(desc),
        "canonical": SITE + url, "comp": comp_key, "key": esc(game_key(m)), "nav": nav(comp_key),
        "back": PAGES[comp_key][0],
        "featured": pitch_card(g, comp_name, today, svg), "panel": detail_panel(detail),
    })
    write(url, page)
    return url


def build_sitemap(urls):
    day = now_sast().date().isoformat()
    rows = "".join(f"  <url><loc>{SITE}{u}</loc><lastmod>{day}</lastmod></url>\n" for u in urls if not u.startswith("/match/"))
    rows += "".join(f"  <url><loc>{SITE}{u}</loc></url>\n" for u in urls if u.startswith("/match/"))
    rows += "".join(f"  <url><loc>{SITE}/{p}</loc></url>\n" for p in INFO_PAGES)
    # plain-text copy (one address per line); Google accepts this format too
    all_urls = [f"{SITE}{u}" for u in urls] + [f"{SITE}/{p}" for p in INFO_PAGES]
    (ROOT / "sitemap.txt").write_text("\n".join(all_urls) + "\n", encoding="utf-8")
    (ROOT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
                                      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                      f"{rows}</urlset>\n", encoding="utf-8")


def run():
    today = now_sast().date()
    svg = pitch_svg()
    home_t = (ROOT / "templates" / "home.html").read_text(encoding="utf-8")
    abc_t = (ROOT / "templates" / "abc.html").read_text(encoding="utf-8")
    comps = load_comps()
    SCORERS.clear()
    SCORERS.update(build_scorers(comps))
    CLUBS.clear()
    clubs = {}
    for c in comps.values():
        for r in c.get("log", []):
            CLUBS.add(slug(r["team"]))
            clubs.setdefault(slug(r["team"]), r["team"])
    urls = [build_comp(s, home_t, svg, today) for s in PAGES]
    urls.append(build_abc(abc_t, today))

    club_t = (ROOT / "templates" / "club.html").read_text(encoding="utf-8")
    club_urls = [build_club(name, comps, club_t, svg, today) for name in clubs.values()]

    game_t = (ROOT / "templates" / "game.html").read_text(encoding="utf-8")
    match_urls = set()
    for k, c in comps.items():
        for m in c.get("results", []) + c.get("fixtures", []):
            if m.get("date") and match_url(m) not in match_urls:
                match_urls.add(build_match(m, k, comps, game_t, svg, today))
    # remove pages of games that moved or no longer exist
    mdir = ROOT / "match"
    if mdir.exists():
        for d in mdir.iterdir():
            if d.is_dir() and f"/match/{d.name}/" not in match_urls:
                for f in d.iterdir():
                    f.unlink()
                d.rmdir()
    build_sitemap(urls + club_urls + sorted(match_urls))
    print(f"Built {len(urls)} competition pages, {len(club_urls)} club pages, {len(match_urls)} match pages")


if __name__ == "__main__":
    run()
