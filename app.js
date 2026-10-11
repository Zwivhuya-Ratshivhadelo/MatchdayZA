/* MatchdayZA front end.
   Loads the scraped data from data/ and fills elements marked data-md="...".
   Each page says which page it is with <body data-page="home|abc|match">. */

const PSL = {
  "betway-premiership": { name: "Betway Premiership" },
  "national-first-division": { name: "Motsepe Foundation Championship" },
  "mtn8": { name: "MTN8" },
  "carling-knockout": { name: "Carling Knockout" },
  "nedbank-cup": { name: "Nedbank Cup" },
};
const BIG_CLUBS = ["kaizer-chiefs", "orlando-pirates", "mamelodi-sundowns"];
const RESULTS_SHOWN = 6;

/* 3-letter codes shown on match cards. Clubs not listed get one made from their name. */
const CODES = {
  "amazulu-fc": "AMA", "chippa-united": "CHP", "durban-city": "DUR", "golden-arrows": "ARR",
  "kaizer-chiefs": "KCH", "kruger-united": "KRU", "mamelodi-sundowns": "SUN", "marumo-gallants": "MAR",
  "milford-fc": "MIL", "orlando-pirates": "PIR", "polokwane-city": "POL", "richards-bay": "RBY",
  "sekhukhune-united": "SEK", "siwelele": "SIW", "stellenbosch-fc": "STE", "ts-galaxy": "GAL",
  "cape-town-city-fc": "CTC", "magesi-fc": "MAG", "hungry-lions-fc": "HUN", "real-native-fc": "RNA",
  "upington-city": "UPC", "pretoria-university-fc": "TUK", "leicesterford-city-fc": "LEI", "highbury": "HIG",
  "hope": "HOP", "gomora-united": "GOM", "lerumo-lions": "LER", "midlands-wanderers": "MID",
  "north-west-university": "NWU", "the-bees": "BEE", "orbit-college-fc": "ORB", "venda-fc": "VEN",
};

/* Pitch drawing behind the featured match (real 105 x 68 m proportions) */
const PITCH_SVG = `<svg class="pitch-svg" viewBox="-6 -6 1062 692" preserveAspectRatio="none" aria-hidden="true"><rect x="-6" y="-6" width="1062" height="692" fill="#0B6A41"/><rect x="0" y="0" width="75" height="680" fill="#0B6A41"/><rect x="75" y="0" width="75" height="680" fill="#0F7A4C"/><rect x="150" y="0" width="75" height="680" fill="#0B6A41"/><rect x="225" y="0" width="75" height="680" fill="#0F7A4C"/><rect x="300" y="0" width="75" height="680" fill="#0B6A41"/><rect x="375" y="0" width="75" height="680" fill="#0F7A4C"/><rect x="450" y="0" width="75" height="680" fill="#0B6A41"/><rect x="525" y="0" width="75" height="680" fill="#0F7A4C"/><rect x="600" y="0" width="75" height="680" fill="#0B6A41"/><rect x="675" y="0" width="75" height="680" fill="#0F7A4C"/><rect x="750" y="0" width="75" height="680" fill="#0B6A41"/><rect x="825" y="0" width="75" height="680" fill="#0F7A4C"/><rect x="900" y="0" width="75" height="680" fill="#0B6A41"/><rect x="975" y="0" width="75" height="680" fill="#0F7A4C"/><g fill="none" stroke="#fff" stroke-opacity=".75" stroke-width="4"><rect x="0" y="0" width="1050" height="680"/><line x1="525" y1="0" x2="525" y2="680"/><circle cx="525" cy="340" r="91.5"/><rect x="0" y="138.5" width="165" height="403"/><rect x="0" y="248.5" width="55" height="183"/><path d="M165 266.9 A91.5 91.5 0 0 1 165 413.1"/><rect x="885" y="138.5" width="165" height="403"/><rect x="995" y="248.5" width="55" height="183"/><path d="M885 266.9 A91.5 91.5 0 0 0 885 413.1"/><path d="M0 10 A10 10 0 0 0 10 0"/><path d="M1040 0 A10 10 0 0 0 1050 10"/><path d="M10 680 A10 10 0 0 0 0 670"/><path d="M1050 670 A10 10 0 0 0 1040 680"/></g><g fill="#fff" fill-opacity=".8"><circle cx="525" cy="340" r="6"/><circle cx="110" cy="340" r="5"/><circle cx="940" cy="340" r="5"/></g><rect x="-6" y="-6" width="1062" height="692" fill="#002A1A" fill-opacity=".22"/></svg>`;

/* ---------- helpers ---------- */
const $ = (sel) => document.querySelector(sel);
const $all = (sel) => [...document.querySelectorAll(sel)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const slug = (s) => String(s || "").normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
const param = (k) => new URLSearchParams(location.search).get(k);

function clubCode(name) {
  const s = slug(name);
  if (CODES[s]) return CODES[s];
  const words = String(name).replace(/\b(FC|F\.C\.|Football Club|United|City)\b/gi, "").trim().split(/\s+/).filter(Boolean);
  if (words.length >= 3) return words.slice(0, 3).map((w) => w[0]).join("").toUpperCase();
  return (words[0] || name).replace(/[^A-Za-z]/g, "").slice(0, 3).toUpperCase();
}
/* Club logo from logos/<club-name>.png. If the file doesn't exist, nothing is shown. */
function crest(name, size) {
  const st = size ? ` style="--size:${size}px"` : "";
  return `<span class="crest"${st}><img src="logos/${slug(name)}.png" alt="" onerror="this.parentNode.remove()"></span>`;
}

const parseDate = (m) => (m.date ? new Date(m.date.includes("T") ? m.date : m.date + "T12:00:00+02:00") : null);
const dayKey = (d) => d.toLocaleDateString("en-CA", { timeZone: "Africa/Johannesburg" });
function dayLabel(m) {
  const d = parseDate(m);
  if (!d) return "Date to be confirmed";
  const today = new Date();
  const k = dayKey(d), plus = (n) => dayKey(new Date(today.getTime() + n * 864e5));
  if (k === plus(0)) return "Today";
  if (k === plus(1)) return "Tomorrow";
  if (k === plus(-1)) return "Yesterday";
  return d.toLocaleDateString("en-ZA", { weekday: "short", day: "numeric", month: "short", timeZone: "Africa/Johannesburg" });
}
function barDate(m) {
  const d = parseDate(m);
  if (!d) return "";
  const p = Object.fromEntries(new Intl.DateTimeFormat("en-GB", { weekday: "short", day: "2-digit", month: "2-digit", year: "numeric", timeZone: "Africa/Johannesburg" })
    .formatToParts(d).map((x) => [x.type, x.value]));
  return `<span class="wd">${p.weekday} </span>${p.day}.${p.month}.${p.year}`;
}
const kickoff = (m) => (m.date && m.date.includes("T") ? m.date.slice(11, 16) : "");
const isPlayed = (m) => m.status === "FT" || m.status === "LIVE";
const byDate = (a, b) => (a.date || "").localeCompare(b.date || "");
const gameKey = (m) => (m.match_id ? `id${m.match_id}` : slug(`${(m.date || "").slice(0, 10)}-${m.home}-${m.away}`));

/* ---------- data ---------- */
async function getJSON(path) {
  try { const r = await fetch(path, { cache: "no-cache" }); return r.ok ? r.json() : null; } catch { return null; }
}
async function loadComps() {
  if (window.MATCHDAY_DATA) return window.MATCHDAY_DATA.comps;   // used by previews
  const comps = {};
  await Promise.all(Object.keys(PSL).map(async (s) => { comps[s] = await getJSON(`data/psl/${s}.json`); }));
  return comps;
}
async function loadStreams() {
  if (window.MATCHDAY_DATA) return window.MATCHDAY_DATA.streams;
  const index = (await getJSON("data/abc/streams.json")) || { streams: [] };
  return (await Promise.all(index.streams.map((s) => getJSON(`data/abc/${s.stream_id}.json`)))).filter(Boolean);
}
async function loadMatch(id) {
  if (window.MATCHDAY_DATA) return (window.MATCHDAY_DATA.matches || {})[id] || null;
  return getJSON(`data/psl/matches/${id}.json`);
}

/* ---------- shared pieces ---------- */
/* Small swipe card for the next-matches row; live games open the match page */
/* opts.pick: the card is a button that puts the game on the pitch; opts.selected: it is the one showing */
function matchCard(m, opts = {}) {
  const live = m.status === "LIVE";
  const top = live ? `<span class="pill-live">Live ${esc(m.minute || "")}</span>` : `<span>${esc(dayLabel(m))}</span>`;
  const right = live ? "" : kickoff(m) || "TBC";
  const row = (team, sc) => `<div class="mcard-row">${crest(team, 26)}<span class="code">${esc(team)}</span>${live ? `<span class="sc">${sc}</span>` : ""}</div>`;
  const inner = `<div class="mcard-top">${top}<span>${esc(right)}</span></div>${row(m.home, m.home_score)}${row(m.away, m.away_score)}`;
  const cls = `mcard ${live ? "live" : ""} ${opts.selected ? "selected" : ""}`;
  return opts.pick ? `<button type="button" class="${cls}" data-key="${esc(gameKey(m))}" aria-pressed="${!!opts.selected}">${inner}</button>`
                   : `<div class="${cls}">${inner}</div>`;
}

/* Result card (LaLiga-style); with opts.pick, tapping it puts the game on the pitch */
function resultCard(m, label, opts = {}) {
  const live = m.status === "LIVE";
  const side = (team) => `<span class="lc-team"><b>${esc(team)}</b>${crest(team, 30)}</span>`;
  const sideR = (team) => `<span class="lc-team">${crest(team, 30)}<b>${esc(team)}</b></span>`;
  const inner = `<div class="lc-bar"><span class="dt">${barDate(m)}</span><span>${live ? `<span class="pill-live">Live ${esc(m.minute || "")}</span>` : "FT"}</span></div>
    <div class="lc-body">${side(m.home)}<span class="lc-score">${m.home_score} - ${m.away_score}</span>${sideR(m.away)}</div>
    ${label ? `<div class="lc-comp">${esc(label)}</div>` : ""}`;
  return opts.pick ? `<button type="button" class="lc pick" data-key="${esc(gameKey(m))}">${inner}<span class="lc-more">View match</span></button>`
                   : `<article class="lc">${inner}</article>`;
}

/* Featured match drawn on the pitch */
function pitchCard(m, compName) {
  const played = isPlayed(m);
  const live = m.status === "LIVE";
  const centre = played
    ? `${m.home_score} - ${m.away_score}<small>${live ? "Live " + esc(m.minute || "") : "Full time"}</small>`
    : `${kickoff(m) || "TBC"}<small>${esc(dayLabel(m))}</small>`;
  const latest = live && m.latest ? `<div class="featured-latest">${esc(m.latest)}</div>` : "";
  const body = `${PITCH_SVG}
    <div class="featured-meta"><span class="featured-comp">${esc(compName)}</span></div>
    <div class="featured-main">
      <div class="featured-team">${crest(m.home)}<strong>${esc(m.home)}</strong></div>
      <div class="featured-score">${centre}</div>
      <div class="featured-team">${crest(m.away)}<strong>${esc(m.away)}</strong></div>
    </div>
    ${latest}
    ${m.venue ? `<div class="featured-venue">${esc(m.venue)}</div>` : ""}`;
  return `<article class="featured">${body}</article>`;
}

function resultsList(box, list, labelOf, opts = {}) {
  if (!list.length) return false;
  const cards = list.map((m, i) => resultCard(m, labelOf ? labelOf(m) : "", opts).replace(/^<(button|article) (type="button" )?class="lc/, (x) => (i >= RESULTS_SHOWN ? x + " extra" : x))).join("");
  box.innerHTML = `<div class="rcards">${cards}</div>` +
    (list.length > RESULTS_SHOWN ? `<button class="more-btn" type="button">Show all results</button>` : "");
  const btn = box.querySelector(".more-btn");
  btn?.addEventListener("click", () => { box.querySelector(".rcards").classList.add("show-all"); btn.remove(); });
  return true;
}

function standingsTable(rows) {
  const body = rows.map((r) => `<tr>
    <td class="pos">${r.pos}</td>
    <td class="club"><div>${crest(r.team)}${esc(r.team)}</div></td>
    <td>${r.p}</td><td class="hide-sm">${r.w}</td><td class="hide-sm">${r.d}</td><td class="hide-sm">${r.l}</td>
    <td>${r.gd == null ? "–" : r.gd > 0 ? "+" + r.gd : r.gd}</td>
    <td class="pts">${r.pts}</td>
    <td class="form hide-sm">${(r.form || []).map((f) => `<span class="${f}">${f}</span>`).join("")}</td>
  </tr>`).join("");
  return `<div class="table-wrap"><table class="standings">
    <thead><tr><th></th><th class="club">Club</th><th title="Played">P</th><th class="hide-sm" title="Won">W</th>
    <th class="hide-sm" title="Drawn">D</th><th class="hide-sm" title="Lost">L</th><th title="Goal difference">GD</th>
    <th title="Points">Pts</th><th class="hide-sm">Form</th></tr></thead><tbody>${body}</tbody></table></div>`;
}

/* Form and goal difference from stored results */
function enrichLog(log, results, extra) {
  const games = {};
  const ids = new Set((results || []).map((r) => r.match_id).filter(Boolean));
  const all = [...(results || []), ...(extra || []).filter((e) => !ids.has(e.match_id))];
  for (const r of all.sort(byDate)) {
    if (r.status !== "FT") continue;
    (games[slug(r.home)] ||= []).push([r.home_score, r.away_score]);
    (games[slug(r.away)] ||= []).push([r.away_score, r.home_score]);
  }
  return (log || []).map((row) => {
    const g = games[slug(row.team)] || [];
    const form = g.slice(-5).map(([f, a]) => (f > a ? "W" : f === a ? "D" : "L"));
    const gd = row.gd ?? (g.length && g.length === row.p ? g.reduce((s, [f, a]) => s + f - a, 0) : null);
    return { ...row, form, gd };
  });
}

/* Switch row: links styled as tabs with a gold underline on the active one */
function switchRow(el, items, active, onPick) {
  el.innerHTML = items.map((it) => `<a href="${it.href}" data-k="${esc(it.key)}" ${it.page ? 'data-page="1"' : ""} ${it.key === active ? 'aria-current="page"' : ""}>${esc(it.label)}</a>`).join("");
  el.querySelectorAll("a:not([data-page])").forEach((a) => a.addEventListener("click", (e) => {
    e.preventDefault();
    onPick(a.dataset.k);
  }));
  el.querySelector('[aria-current="page"]')?.scrollIntoView({ inline: "center", block: "nearest" });
}

/* The competition row, identical on every page. On the home page PSL items switch in place;
   everywhere else they are normal links. ABC Motsepe League always opens its own page. */
function compNav(active, onPick) {
  const el = $('[data-md="comp-switch"]');
  if (!el) return;
  const items = Object.entries(PSL).map(([k, c]) => ({ key: k, label: c.name, href: k === "betway-premiership" ? "index.html" : `index.html?c=${k}`, page: !onPick }));
  items.push({ key: "abc", label: "ABC Motsepe League", href: "abc.html", page: true });
  switchRow(el, items, active, onPick || (() => {}));
}

function liveRefresh(on) {
  clearTimeout(window.__mdRefresh);
  if (on && !window.MATCHDAY_DATA) window.__mdRefresh = setTimeout(() => location.reload(), 60000);
}

/* ---------- home: PSL competitions, one switch drives the page ---------- */
async function renderHome() {
  const comps = await loadComps();
  let current = PSL[param("c")] ? param("c") : "betway-premiership";
  let chosen = param("m");          // the game on the pitch (from a tap, or a shared link)
  let drawToken = 0;

  const setUrl = () => {
    const q = new URLSearchParams();
    if (current !== "betway-premiership") q.set("c", current);
    if (chosen) q.set("m", chosen);
    history.replaceState(null, "", q.toString() ? `?${q}` : location.pathname);
  };

  const draw = () => {
    const comp = comps[current] || {};
    const name = PSL[current].name;
    const tag = (m) => ((m._comp = current), m);
    const fixtures = (comp.fixtures || []).map(tag).sort(byDate);
    const results = (comp.results || []).map(tag);
    const live = results.filter((m) => m.status === "LIVE");
    const games = [...live, ...fixtures, ...results];

    compNav(current, (k) => { current = k; chosen = null; setUrl(); draw(); });

    // which game is on the pitch: the chosen one, else live, else next big-club game, else next game, else latest result
    const auto = live[0]
      || fixtures.find((m) => BIG_CLUBS.includes(slug(m.home)) || BIG_CLUBS.includes(slug(m.away)))
      || fixtures[0] || [...results].sort(byDate).reverse()[0];
    const pick = games.find((m) => gameKey(m) === chosen) || auto;
    const pickKey = pick ? gameKey(pick) : null;

    const next = [...live, ...fixtures].slice(0, 12);
    const title = $('[data-md="next-title"]');
    if (title) title.textContent = live.length ? "Live now" : "Next matches";
    $('[data-md="next-matches"]').innerHTML = next.length
      ? next.map((m) => matchCard(m, { pick: true, selected: gameKey(m) === pickKey })).join("")
      : `<p class="empty">No ${esc(name)} matches scheduled yet.</p>`;

    const done = results.filter((m) => m.status === "FT").sort(byDate).reverse();
    const resBox = $('[data-md="results"]');
    if (!resultsList(resBox, done, null, { pick: true })) resBox.innerHTML = `<p class="empty">No ${esc(name)} results yet.</p>`;

    const hasLog = (comp.log || []).length > 0;
    $('[data-md="log-section"]').hidden = !hasLog;
    $('[data-md="standings"]').innerHTML = hasLog ? standingsTable(enrichLog(comp.log, comp.results, comp.extra)) : "";

    // pitch first with what we know, then the game's details once loaded
    const feat = $('[data-md="featured"]'), panel = $('[data-md="match-panel"]');
    feat.innerHTML = pick ? pitchCard(pick, name) : "";
    panel.innerHTML = "";
    const token = ++drawToken;
    if (pick) {
      (pick.match_id ? loadMatch(pick.match_id) : Promise.resolve(null)).then((detail) => {
        if (token !== drawToken) return;   // the user picked another game meanwhile
        const m = { ...pick };
        if (detail && detail.status !== "NS") Object.assign(m, { home_score: detail.home_score, away_score: detail.away_score, status: detail.status, minute: detail.minute ?? m.minute });
        if (detail) feat.innerHTML = pitchCard(m, name);
        panel.innerHTML = detailPanel(m, detail);
      });
    }

    liveRefresh(live.length > 0 || pick?.status === "LIVE");
  };

  // tapping a next-match card or a result card puts that game on the pitch
  document.addEventListener("click", (e) => {
    const card = e.target.closest("[data-key]");
    if (!card) return;
    chosen = card.dataset.key;
    setUrl();
    draw();
    if (card.classList.contains("lc")) $('[data-md="featured"]').scrollIntoView({ behavior: "smooth", block: "start" });
  });
  draw();
}

/* ---------- ABC Motsepe League: province and stream filters ---------- */
async function renderAbc() {
  compNav("abc");
  const streams = await loadStreams();
  const box = $('[data-md="abc-content"]');
  if (!streams.length) { box.innerHTML = `<p class="empty">ABC Motsepe League data appears after the first update.</p>`; return; }
  const provinces = [...new Set(streams.map((s) => s.province || "Other"))].sort();
  let current = streams.find((s) => s.stream_id === param("s")) || streams.find((s) => s.province === provinces[0]);
  const provSel = $('[data-md="province-select"]'), streamSel = $('[data-md="stream-select"]');

  const draw = () => {
    const prov = current.province || "Other";
    const inProv = streams.filter((s) => (s.province || "Other") === prov);
    provSel.innerHTML = provinces.map((p) => `<option ${p === prov ? "selected" : ""}>${esc(p)}</option>`).join("");
    streamSel.innerHTML = inProv.map((s) => `<option value="${esc(s.stream_id)}" ${s === current ? "selected" : ""}>${esc(s.name)}</option>`).join("");
    streamSel.closest("label").hidden = inProv.length < 2;

    const fixtures = [...(current.fixtures || [])].sort(byDate).slice(0, 12);
    $('[data-md="next-matches"]').innerHTML = fixtures.length ? fixtures.map(matchCard).join("") : `<p class="empty">No fixtures listed for ${esc(current.name)} yet.</p>`;
    const done = (current.results || []).filter((m) => m.status === "FT").sort(byDate).reverse();
    const resBox = $('[data-md="results"]');
    if (!resultsList(resBox, done)) resBox.innerHTML = `<p class="empty">No results for ${esc(current.name)} yet.</p>`;
    const hasLog = (current.log || []).length > 0;
    $('[data-md="log-section"]').hidden = !hasLog;
    $('[data-md="standings"]').innerHTML = hasLog ? standingsTable(enrichLog(current.log, current.results)) : "";
  };
  const go = () => { history.replaceState(null, "", `?s=${current.stream_id}`); draw(); };
  provSel.addEventListener("change", () => { current = streams.find((s) => (s.province || "Other") === provSel.value); go(); });
  streamSel.addEventListener("change", () => { current = streams.find((s) => s.stream_id === streamSel.value); go(); });
  draw();
}

/* ---------- match page: pitch header, timeline, stats ---------- */
const EVENT_TEXT = {
  goal: (e) => `Goal! ${e.player} (${e.team})`,
  penalty_goal: (e) => `Penalty scored by ${e.player} (${e.team})`,
  own_goal: (e) => `Own goal by ${e.player} (${e.team})`,
  penalty_saved: (e) => `Penalty saved, ${e.player} (${e.team}) denied`,
  penalty_missed: (e) => `Penalty missed by ${e.player} (${e.team})`,
  penalty_won: (e) => `Penalty to ${e.team}, ${e.player} fouled`,
  yellow: (e) => `Yellow card, ${e.player} (${e.team})`,
  second_yellow: (e) => `Second yellow, ${e.player} (${e.team}) sent off`,
  red: (e) => `Red card, ${e.player} (${e.team})`,
  sub: (e) => `${e.team}: ${e.player_in} on, ${e.player_out} off`,
  var: () => "VAR check",
};
const PERIOD_TEXT = { kickoff: "Kick-off", half_time: "Half-time", second_half: "Second half", full_time: "Full time", extra_time: "Extra time", shootout: "Penalty shootout" };
const ICON = {
  goal: '<span class="ev-ico goal">⚽</span>', penalty_goal: '<span class="ev-ico goal">⚽</span>', own_goal: '<span class="ev-ico goal og">⚽</span>',
  yellow: '<span class="ev-ico card y"></span>', red: '<span class="ev-ico card r"></span>', second_yellow: '<span class="ev-ico card yr"></span>',
  sub: '<span class="ev-ico sub">⇄</span>', penalty_saved: '<span class="ev-ico miss">✕</span>', penalty_missed: '<span class="ev-ico miss">✕</span>',
  penalty_won: '<span class="ev-ico pen">P</span>', var: '<span class="ev-ico var">VAR</span>',
};

/* Stats, key moments and line-ups for the game on the pitch */
function detailPanel(m, detail) {
  const events = detail?.events || [], stats = detail?.stats || [], lineups = detail?.lineups || [];
  const parts = [];
  if (stats.length) {
    parts.push(`<section class="panel"><div class="panel-head"><h2>Stats</h2></div>${stats.map((st) => {
      const h = parseFloat(st.home) || 0, a = parseFloat(st.away) || 0, tot = h + a || 1;
      return `<div class="stat"><div class="stat-row"><b>${esc(st.home)}</b><span>${esc(st.label)}</span><b>${esc(st.away)}</b></div>
        <div class="stat-bar"><i class="h" style="width:${(h / tot) * 100}%"></i><i class="a" style="width:${(a / tot) * 100}%"></i></div></div>`;
    }).join("")}</section>`);
  }
  if (events.length) {
    const body = `<ol class="timeline">${events.map((e) => {
      if (PERIOD_TEXT[e.type]) return `<li class="ev-period"><span>${PERIOD_TEXT[e.type]}</span></li>`;
      const text = (EVENT_TEXT[e.type] || (() => ""))(e);
      const score = e.score ? `<b class="ev-score">${e.score[0]} - ${e.score[1]}</b>` : "";
      return `<li class="ev ev-${e.type}"><span class="ev-min">${esc(e.minute)}</span>${ICON[e.type] || ""}<span class="ev-text">${esc(text)}</span>${score}</li>`;
    }).join("")}</ol>`;
    parts.push(`<section class="panel"><div class="panel-head"><h2>Key moments</h2></div>${body}</section>`);
  }
  if (lineups.length) {
    const list = (ps) => ps.map((p) => `<li><span class="lu-no">${esc(p.no)}</span><span class="lu-name">${esc(p.name)}</span><span class="lu-pos">${esc(p.pos)}</span></li>`).join("");
    parts.push(`<section class="panel"><div class="panel-head"><h2>Line-ups</h2></div><div class="lineups">${lineups.map((t) => `<div class="lu-team">
      <h3>${crest(t.team, 24)}${esc(t.team)}</h3>
      <h4>Starting XI</h4><ol class="lu-list">${list(t.starting)}</ol>
      ${t.subs.length ? `<h4>Substitutes</h4><ol class="lu-list">${list(t.subs)}</ol>` : ""}
    </div>`).join("")}</div></section>`);
  }
  return parts.join("");
}

/* Old match-page links now open the game on the home page */
function renderMatch() {
  const c = PSL[param("c")] ? param("c") : "betway-premiership", id = param("id");
  location.replace(`index.html?c=${c}${id ? `&m=id${id}` : ""}`);
}

/* ---------- start ---------- */
$all('[data-md="year"]').forEach((el) => (el.textContent = new Date().getFullYear()));
({ home: renderHome, abc: renderAbc, match: renderMatch, info: () => compNav(null) }[document.body.dataset.page] || renderHome)();
