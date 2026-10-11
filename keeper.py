"""Keeps the site updating when GitHub's own schedule doesn't fire.

Runs inside the "Keep running" workflow for about 5.5 hours:
  - every hour at :23 (SAST) it runs the normal update (update.py) and pushes the data
  - 80 minutes before a PSL kick-off it runs the live loop (live.py) for that game window
Then it starts the next "Keep running" workflow and exits, so there is always one running.
If GitHub's own schedule has started working, it stops chaining and leaves it to that.

Run:  python keeper.py   (pushing a change to this file restarts it with the latest code)
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

from common import DATA, load_json, now_sast

RUN_FOR = timedelta(hours=5, minutes=20)
JOB_LIMIT = timedelta(hours=5, minutes=50)    # the workflow is stopped at 6 hours
UPDATE_MINUTE = 23
LEAD = timedelta(minutes=80)
WINDOWS = {"a": (0, 15 * 60 + 30), "b": (15 * 60 + 30, 17 * 60 + 30),
           "c": (17 * 60 + 30, 19 * 60 + 30), "d": (19 * 60 + 30, 24 * 60)}
REPO = os.environ.get("GITHUB_REPOSITORY", "")


def sh(*cmd):
    print("$", " ".join(cmd), flush=True)
    return subprocess.run(cmd, check=False)


def gh_json(*args):
    try:
        out = subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout
        return json.loads(out or "[]")
    except Exception as e:
        print(f"gh failed: {e}")
        return []


def schedule_working():
    """True when GitHub's own hourly schedule has run in the last 2 hours."""
    runs = gh_json("run", "list", "--repo", REPO, "--workflow", "update.yml", "--event", "schedule",
                   "--limit", "1", "--json", "createdAt")
    if not runs:
        return False
    when = datetime.fromisoformat(runs[0]["createdAt"].replace("Z", "+00:00"))
    return datetime.now(timezone.utc) - when < timedelta(hours=2)


def pull():
    sh("git", "pull", "-q", "--rebase", "-X", "theirs")


def update():
    pull()
    sh(sys.executable, "update.py")
    sh("bash", "commit.sh")


def kickoffs_today():
    """{window: first kick-off} for today's PSL games."""
    today = now_sast().date().isoformat()
    first = {}
    for f in (DATA / "psl").glob("*.json"):
        comp = load_json(f, {})
        games = comp.get("fixtures", []) + [r for r in comp.get("results", []) if r.get("status") == "LIVE"]
        for m in games:
            d = m.get("date") or ""
            if d[:10] != today or "T" not in d:
                continue
            ko = datetime.fromisoformat(d)
            mins = ko.hour * 60 + ko.minute
            w = next(k for k, (lo, hi) in WINDOWS.items() if lo <= mins < hi)
            first[w] = min(first.get(w, ko), ko)
    return first


def next_keeper():
    sh("gh", "workflow", "run", "keep.yml", "--repo", REPO, "--ref", "main")


def main():
    start = now_sast()
    done_hours, done_windows = set(), set()
    if schedule_working():
        print("GitHub's own schedule is running; nothing to do.")
        return
    while now_sast() - start < RUN_FOR:
        now = now_sast()
        # live games first: the live loop runs until its games end
        for w, ko in sorted(kickoffs_today().items()):
            key = (now.date(), w)
            if key not in done_windows and ko - LEAD <= now < ko + timedelta(hours=2):
                if ko + timedelta(hours=2, minutes=30) > start + JOB_LIMIT:
                    print("Not enough time left in this run for the live games; handing over.")
                    next_keeper()
                    return
                done_windows.add(key)
                pull()
                sh(sys.executable, "live.py", w)
                now = now_sast()
        # hourly update
        hour = (now.date(), now.hour)
        if now.minute >= UPDATE_MINUTE and hour not in done_hours:
            done_hours.add(hour)
            update()
        time.sleep(60)

    if schedule_working():
        print("GitHub's own schedule is running now; not starting another keeper.")
        return
    next_keeper()


if __name__ == "__main__":
    main()
