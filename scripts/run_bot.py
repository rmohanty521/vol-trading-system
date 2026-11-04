"""Rebalance the paper portfolio once, and report metrics to Datadog.

Default is a dry run: prints the orders it would send and trades nothing.
--paper sends real orders to your Alpaca PAPER account (needs
ALPACA_API_KEY / ALPACA_SECRET_KEY). There is no live-money mode.

usage:
    python scripts/run_bot.py                 # dry run
    python scripts/run_bot.py --paper         # paper trade
    python scripts/run_bot.py --paper --pnl   # only report equity / P&L, no trading
"""

import json
import sys
import traceback

from voltrade import config
from voltrade.live import AlpacaBroker, DryRunBroker, compute_targets, rebalance
from voltrade.monitoring import Metrics


def main(argv, metrics):
    paper = "--paper" in argv
    broker = AlpacaBroker() if paper else DryRunBroker()

    metrics.record_portfolio(broker.equity(), broker.last_equity())
    if "--pnl" in argv:
        return

    if not broker.is_open():
        print("market closed, nothing to do")
        return

    targets, fc_vol, asof = compute_targets()
    metrics.record_forecasts(fc_vol)
    print(f"signal as of {asof.date()}: gross target {targets.sum():.2f}x, "
          f"vol target {config.VOL_TARGET:.0%}")
    print("top weights:", targets.sort_values(ascending=False).head(5).round(3).to_dict())

    results, summary = rebalance(broker, targets)
    for r in results:
        print(f"  {r.side:4} {r.symbol:5} ${r.notional:>10,.2f}  {r.status}")
    print(json.dumps(summary, indent=2))

    metrics.record_rebalance(results, summary)
    metrics.event("voltrade rebalance",
                  f"{summary['n_orders']} orders, ${summary['traded_notional']:,.0f} traded, "
                  f"fill rate {summary['fill_rate']}")


def run(argv):
    """Entry point shared by the CLI and scripts/ci_run.py. Always flushes metrics."""
    metrics = Metrics(tags=[f"mode:{'paper' if '--paper' in argv else 'dry_run'}"])
    try:
        main(argv, metrics)
    except Exception:
        metrics.event("voltrade bot failed", traceback.format_exc()[-2000:], alert_type="error")
        raise
    finally:
        metrics.flush()


if __name__ == "__main__":
    run(sys.argv[1:])
