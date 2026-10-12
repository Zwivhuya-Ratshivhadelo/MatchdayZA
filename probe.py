"""One-off run in GitHub Actions (starts when this file changes): fill final scores and goal 
minutes from 365scores, then rebuild the pages."""
import build
import psl

psl.fill_from_365()
build.run()
