"""Plot the Alpaca paper account's daily equity and P&L.

Reads ALPACA_API_KEY / ALPACA_SECRET_KEY from the environment (paper keys).

usage: python scripts/plot_pnl.py [--since 2026-11-03] [--until 2026-11-23] [--out docs/paper_pnl.png]
"""

import argparse
import os
from datetime import date, datetime, timezone

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from alpaca.trading.client import TradingClient  # noqa: E402
from alpaca.trading.requests import GetPortfolioHistoryRequest  # noqa: E402


def history(since, until):
    client = TradingClient(os.environ["ALPACA_API_KEY"], os.environ["ALPACA_SECRET_KEY"], paper=True)
    h = client.get_portfolio_history(GetPortfolioHistoryRequest(
        timeframe="1D",
        start=datetime.combine(since, datetime.min.time(), timezone.utc),
        end=datetime.combine(until, datetime.max.time(), timezone.utc),
    ))
    days = [datetime.fromtimestamp(t, timezone.utc).date() for t in h.timestamp]
    return days, h.equity, h.profit_loss


def plot(days, equity, pnl, out):
    fig, (ax_eq, ax_pnl) = plt.subplots(2, 1, figsize=(9, 5.5), sharex=True,
                                        gridspec_kw={"height_ratios": [2, 1]})
    ax_eq.plot(days, equity, color="#2a6fdb", lw=2)
    ax_eq.set_ylabel("equity ($)")
    ax_eq.yaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter("{x:,.0f}"))
    ax_eq.set_title(f"Alpaca paper account, {days[0]:%b %-d} to {days[-1]:%b %-d, %Y}")

    ax_pnl.bar(days, pnl, color=["#2e9e5b" if p >= 0 else "#d1453b" for p in pnl], width=0.7)
    ax_pnl.axhline(0, color="#888", lw=0.8)
    ax_pnl.set_ylabel("daily P&L ($)")
    ax_pnl.xaxis.set_major_formatter(mdates.DateFormatter("%b %-d"))

    for ax in (ax_eq, ax_pnl):
        ax.grid(alpha=0.3)
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    print(f"wrote {out}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--since", type=date.fromisoformat, default=date(2026, 11, 3))
    p.add_argument("--until", type=date.fromisoformat, default=date.today())
    p.add_argument("--out", default="docs/paper_pnl.png")
    a = p.parse_args()
    plot(*history(a.since, a.until), a.out)
