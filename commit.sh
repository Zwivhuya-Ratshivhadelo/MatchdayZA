#!/usr/bin/env bash
# Commit changed data/ and logos/ files and push, retrying if another run pushed first.
set -uo pipefail
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
for d in data logos; do
  [ -d "$d" ] && git add "$d"
done
if git diff --cached --quiet; then
  echo "No data changes."
  exit 0
fi
git commit -q -m "Update data $(date -u +%Y-%m-%dT%H:%MZ)"
for i in 1 2 3 4 5; do
  # on a clash, keep this run's fresher files
  if git pull -q --rebase -X theirs && git push -q; then
    echo "Data pushed."
    exit 0
  fi
  sleep $((i * 5))
done
echo "Could not push data after 5 tries."
exit 1
