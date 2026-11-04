"""Entry point for the scheduled GitHub Actions run.

GitHub cron is in UTC and ignores daylight saving, so the workflow fires at
both 19:30 and 20:30 UTC. This script only proceeds when it is 15:xx in
New York, so exactly one of the two runs does anything, all year round.

- Fridays: rebalance (matches config.REBALANCE = W-FRI)
- other weekdays: report equity and P&L only

usage: python scripts/ci_run.py [--force-rebalance | --force-pnl]
"""

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent))
from run_bot import run  # noqa: E402

NY = ZoneInfo("America/New_York")


def decide(now, argv):
    """Return run_bot args for this moment, or None to skip."""
    if "--force-rebalance" in argv:
        return ["--paper"]
    if "--force-pnl" in argv:
        return ["--paper", "--pnl"]
    if now.weekday() >= 5 or now.hour != 15:
        return None
    return ["--paper"] if now.weekday() == 4 else ["--paper", "--pnl"]


if __name__ == "__main__":
    now = datetime.now(NY)
    args = decide(now, sys.argv[1:])
    if args is None:
        print(f"{now:%a %H:%M} New York: outside the 15:00 window, skipping")
        sys.exit(0)
    print(f"{now:%a %H:%M} New York: running run_bot {' '.join(args)}")
    run(args)
