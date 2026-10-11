# MatchdayZA

South African football scores site. GitHub Actions scrapes the data into `data/`, and GitHub Pages
serves the site straight from this repo, so the site updates every time new data is saved.

## Files

| File | What it is |
|---|---|
| `index.html` | Home page: PSL competitions, with the competition switch |
| `abc.html` | ABC Motsepe League page: province and stream switch |
| `match.html` | Match page: score, timeline, stats |
| `style.css` | All the design |
| `app.js` | Loads the data and fills the pages |
| `logos/` | Club logos (you add these, see below) |
| `psl.py` | Scrapes Betway Premiership, Motsepe Foundation Championship, MTN8, Carling Knockout, Nedbank Cup, plus match timelines |
| `abc_league.py` | Scrapes the ABC Motsepe League |
| `live.py` | Follows PSL games minute by minute on match days |
| `common.py` | Shared helpers |
| `commit.sh` | Saves new data to the repo |
| `requirements.txt` | Python packages |
| `.nojekyll` | Tells GitHub Pages to serve files as they are |
| `.gitignore` | Keeps debug files out |
| `.github/workflows/psl.yml` | Runs `psl.py` every hour |
| `.github/workflows/abc.yml` | Runs `abc_league.py` four times a day |
| `.github/workflows/live.yml` | Runs `live.py` every afternoon and evening |

## Setup

1. **Public repository** on GitHub (free Actions and Pages).
2. **Add every file** with exactly the path above. On GitHub: *Add file → Create new file* and type the full path,
   e.g. `.github/workflows/psl.yml`.
3. **Let Actions save data:** *Settings → Actions → General → Workflow permissions → Read and write permissions → Save*.
4. **First data:** *Actions → PSL scores (hourly) → Run workflow*, then *ABC Motsepe League → Run workflow*.
5. **Switch on the site:** *Settings → Pages → Deploy from a branch → `main` / `(root)` → Save*.
   The site is at `https://<username>.github.io/<repo>/`.

If you set this up with the earlier version, delete `build.py`, `deploy.sh` and `inqaku.py`, and you can delete the
`gh-pages` branch.

## Club logos

Put PNG files in `logos/` named exactly like this. A missing logo shows nothing, so add them whenever you have them.

**Betway Premiership:** `amazulu-fc.png`, `chippa-united.png`, `durban-city.png`, `golden-arrows.png`,
`kaizer-chiefs.png`, `kruger-united.png`, `mamelodi-sundowns.png`, `marumo-gallants.png`, `milford-fc.png`,
`orlando-pirates.png`, `polokwane-city.png`, `richards-bay.png`, `sekhukhune-united.png`, `siwelele.png`,
`stellenbosch-fc.png`, `ts-galaxy.png`

**Motsepe Foundation Championship:** `cape-town-city-fc.png`, `gomora-united.png`, `highbury.png`, `hope.png`,
`hungry-lions-fc.png`, `leicesterford-city-fc.png`, `lerumo-lions.png`, `magesi-fc.png`, `midlands-wanderers.png`,
`north-west-university.png`, `orbit-college-fc.png`, `pretoria-university-fc.png`, `real-native-fc.png`,
`the-bees.png`, `upington-city.png`, `venda-fc.png`

Any other club: the team name in lowercase with dashes, e.g. `Tshwane South College FC` → `tshwane-south-college-fc.png`.

## When something breaks

A failed run shows a red ❌ in the Actions tab. Re-run it with **"Save raw pages"** ticked and download the
`psl-raw-pages` or `abc-raw-pages` file at the bottom of the run; it shows exactly what the scraper saw.
Existing data is never wiped by a failed run.
