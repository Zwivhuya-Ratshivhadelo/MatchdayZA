"""Backup for GitHub's scheduler, which skips many scheduled runs (badly so on new repos).

Runs inside the "Keep running" workflow: every 5 minutes it does what runner.py says is due
(an update about hourly, or following live PSL games), and after about 5.5 hours it starts the
next "Keep running" run, so there is always one going. It shares the "site" queue with the
"Site" workflow, so the two never run at the same time and nothing is done twice.

Run:  python keeper.py   (pushing a change to this file restarts it with the latest code)
"""
import os
import subprocess
import sys
import time
from datetime import timedelta

import runner
from common import now_sast

RUN_FOR = timedelta(hours=5, minutes=20)
JOB_LIMIT = timedelta(hours=5, minutes=50)   # GitHub stops a job at 6 hours
LIVE_NEEDS = timedelta(hours=3, minutes=20)  # 80 min lead + a game + extra time
REPO = os.environ.get("GITHUB_REPOSITORY", "")


def sh(*cmd):
    print("$", " ".join(cmd), flush=True)
    return subprocess.run(cmd, check=False).returncode


def next_keeper():
    for _ in range(3):
        if sh("gh", "workflow", "run", "keep.yml", "--repo", REPO, "--ref", "main") == 0:
            return
        time.sleep(20)


def main():
    start = now_sast()
    while now_sast() - start < RUN_FOR:
        now = now_sast()
        if runner.live_window(now) and now + LIVE_NEEDS > start + JOB_LIMIT:
            print("Not enough time left for the live games; handing over to a fresh run.")
            break
        sh("git", "pull", "-q", "--rebase", "-X", "theirs")
        sh(sys.executable, "runner.py")
        time.sleep(300)
    next_keeper()


if __name__ == "__main__":
    main()
