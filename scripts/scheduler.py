"""Long-running scheduler for the deployed bot.

- Every weekday at 15:45 New York time: report equity and daily P&L.
- On rebalance days (Fridays, matching config.REBALANCE): also rebalance.

Passes its arguments through to run_bot (e.g. --paper).

usage: python scripts/scheduler.py --paper
"""

import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
RUN_AT = (15, 45)  # 15 minutes before the close
REBALANCE_WEEKDAY = 4  # Friday
BOT = Path(__file__).with_name("run_bot.py")


def next_run(now):
    run = now.replace(hour=RUN_AT[0], minute=RUN_AT[1], second=0, microsecond=0)
    if run <= now:
        run += timedelta(days=1)
    while run.weekday() >= 5:  # skip weekends
        run += timedelta(days=1)
    return run


if __name__ == "__main__":
    args = sys.argv[1:]
    while True:
        run = next_run(datetime.now(NY))
        print(f"next run {run:%a %Y-%m-%d %H:%M %Z}", flush=True)
        time.sleep(max(0, (run - datetime.now(NY)).total_seconds()))

        extra = [] if run.weekday() == REBALANCE_WEEKDAY else ["--pnl"]
        subprocess.run([sys.executable, str(BOT), *args, *extra])
