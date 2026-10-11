"""One run that updates everything: PSL scores every time, ABC Motsepe League four times a day,
club logos once a day. Run with --all to do all three now (manual runs do this).

Run:  python update.py [--all]
"""
import sys

import abc_league
import logos
import psl
from common import ROOT, now_sast

ABC_HOURS = {6, 12, 18, 22}   # SAST
LOGO_HOUR = 5                 # SAST


def step(name, fn):
    print(f"\n=== {name} ===")
    try:
        fn()
        return True
    except SystemExit as e:
        return not e.code
    except Exception as e:
        print(f"{name} failed: {e}")
        return False


def main():
    everything = "--all" in sys.argv
    hour = now_sast().hour
    ok = step("PSL scores", psl.run)
    if everything or hour in ABC_HOURS:
        ok &= step("ABC Motsepe League", abc_league.run)
    if everything or hour == LOGO_HOUR or not (ROOT / "logos").exists():
        ok &= step("Club logos", logos.run)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
