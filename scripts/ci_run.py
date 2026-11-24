"""Entry point for the scheduled GitHub Actions run.

GitHub cron is in UTC and ignores daylight saving, so the workflow fires at
both 19:30 and 20:30 UTC. Exactly one of those is 15:30 in New York on any
given day; only that one does anything, all year round.

GitHub often starts scheduled runs hours late, so the check uses the time the
run was *scheduled* for (the cron line, passed in as SCHEDULE from
github.event.schedule), not the time it actually started. Without SCHEDULE
(local runs) it falls back to the current time.

- Fridays: rebalance (matches config.REBALANCE = W-FRI). If the run starts
  after the close, run_bot still reports equity / P&L and skips trading.
- other weekdays: report equity and P&L only

usage: SCHEDULE="30 19 * * 1-5" python scripts/ci_run.py [--force-rebalance | --force-pnl]
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent))
from run_bot import run  # noqa: E402

NY = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")


def scheduled_time(now, schedule):
    """Most recent time at or before `now` that the cron line `schedule`
    ("M H ..." in UTC) fired, in New York time."""
    minute, hour = (int(x) for x in schedule.split()[:2])
    now_utc = now.astimezone(UTC)
    fired = now_utc.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if fired > now_utc:
        fired -= timedelta(days=1)
    return fired.astimezone(NY)


def decide(now, argv, schedule=None):
    """Return run_bot args for this moment, or None to skip."""
    if "--force-rebalance" in argv:
        return ["--paper"]
    if "--force-pnl" in argv:
        return ["--paper", "--pnl"]
    when = scheduled_time(now, schedule) if schedule else now
    if when.weekday() >= 5 or when.hour != 15:
        return None
    return ["--paper"] if when.weekday() == 4 else ["--paper", "--pnl"]


if __name__ == "__main__":
    now = datetime.now(NY)
    schedule = os.environ.get("SCHEDULE") or None
    args = decide(now, sys.argv[1:], schedule)
    label = f"scheduled {scheduled_time(now, schedule):%a %H:%M}, " if schedule else ""
    if args is None:
        print(f"{label}now {now:%a %H:%M} New York: not the 15:30 run, skipping")
        sys.exit(0)
    print(f"{label}now {now:%a %H:%M} New York: running run_bot {' '.join(args)}")
    run(args)
