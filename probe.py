"""One-off run in GitHub Actions (starts when this file changes): fill final scores the PSL
hasn't posted yet from 365scores, rebuild the pages, and note what the feed returned."""
import build
import psl
import scores365
from common import DATA, save_json

save_json(DATA / "_probe.json", scores365.games()[:40])
psl.fill_from_365()
build.run()
