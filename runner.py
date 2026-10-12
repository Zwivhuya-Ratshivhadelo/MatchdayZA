"""One check, started every 10 minutes by the "Site" workflow.

GitHub drops some scheduled runs, so instead of one run an hour there are six; each one decides
what is due and most finish in seconds:
  - a PSL game kicks off within 80 minutes (or is on): follow it live until it ends (live.py)
  - the last update is more than 55 minutes old: run the normal update (update.py)
  - otherwise: nothing to do
Data is pushed by commit.sh. Run:  python runner.py
"""
import subprocess
import sys
from datetime import datetime, timedelta

from common import DATA, load_json, now_sast

LEAD = timedelta(minutes=80)
UPDATE_EVERY = timedelta(minutes=55)
WINDOWS = {"a": (0, 15 * 60 + 30), "b": (15 * 60 + 30, 17 * 60 + 30),
           "c": (17 * 60 + 30, 19 * 60 + 30), "d": (19 * 60 + 30, 24 * 60)}
STAMP = DATA / "_last_update.json"


def sh(*cmd):
    print("$", " ".join(cmd), flush=True)
    return subprocess.run(cmd, check=False).returncode


def live_window(now):
    """The game window to follow now, if a PSL game kicks off within 80 minutes or is on."""
    today = now.date().isoformat()
    for f in sorted((DATA / "psl").glob("*.json")):
        comp = load_json(f, {})
        games = comp.get("fixtures", []) + [r for r in comp.get("results", []) if r.get("status") == "LIVE"]
        for m in games:
            d = m.get("date") or ""
            if d[:10] != today or "T" not in d:
                continue
            ko = datetime.fromisoformat(d)
            if ko - LEAD <= now < ko + timedelta(hours=2):
                mins = ko.hour * 60 + ko.minute
                return next(k for k, (lo, hi) in WINDOWS.items() if lo <= mins < hi)
    return None


def main():
    now = now_sast()
    w = live_window(now)
    if w:
        print(f"Game window {w}: following live.")
        sh(sys.executable, "live.py", w)
        return
    last = load_json(STAMP, {}).get("time")
    if last and now - datetime.fromisoformat(last) < UPDATE_EVERY:
        print(f"Last update {last}; nothing due.")
        return
    code = sh(sys.executable, "update.py")
    from common import save_json
    save_json(STAMP, {"time": now_sast().isoformat(timespec="seconds"), "ok": code == 0})
    sh("bash", "commit.sh")


if __name__ == "__main__":
    main()
