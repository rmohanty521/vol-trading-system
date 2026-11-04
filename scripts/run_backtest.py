"""Backtest: forecast-sized vs realized-vol-sized vs equal weight.

Needs reports/oos_preds.parquet from scripts/run_forecast.py.
Runs only over the out-of-sample period, so every forecast used for
sizing came from a model that never saw that date.

usage: python scripts/run_backtest.py [model]   (default: ridge)
"""

import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from voltrade import backtest, config, metrics, sizing
from voltrade.data import load_prices, returns

DOCS = config.ROOT / "docs"

if __name__ == "__main__":
    model = sys.argv[1] if len(sys.argv) > 1 else "ridge"

    px = load_prices()
    ret = returns(px["Close"])
    oos = pd.read_parquet(config.REPORT_DIR / "oos_preds.parquet")

    fc_vol = np.exp(oos[model]).unstack("ticker")
    rv_vol = (ret.rolling(20).std() * np.sqrt(252)).loc[fc_vol.index]
    dates = sizing.rebalance_dates(fc_vol.index)

    weights = {
        "equal weight": sizing.equal_weights(ret.columns, dates),
        "realized-vol sized": sizing.vol_target_weights(rv_vol, ret, dates),
        f"forecast sized ({model})": sizing.vol_target_weights(fc_vol, ret, dates),
    }
    start = max(w.index[0] for w in weights.values())
    end = fc_vol.index[-1]
    window = ret.loc[:end]

    results = {name: backtest.run(w.loc[start:], window) for name, w in weights.items()}

    table = pd.DataFrame({n: metrics.perf_stats(r["ret"]) for n, r in results.items()}).T
    table["Avg exposure"] = [r["exposure"].mean() for r in results.values()]
    table["Ann. turnover"] = [r["turnover"].sum() / len(r) * 252 for r in results.values()]
    table = table.round(3)

    period = f"{start.date()} to {end.date()}"
    print(f"backtest {period}, {len(ret.columns)} stocks, weekly rebalance, "
          f"{config.COST_BPS} bp costs, {config.VOL_TARGET:.0%} vol target, "
          f"{config.MAX_LEVERAGE}x cap")
    print(table.to_markdown())

    config.REPORT_DIR.mkdir(exist_ok=True)
    with open(config.REPORT_DIR / "backtest.md", "w") as f:
        f.write(f"## Backtest {period} (net of costs)\n\n{table.to_markdown()}\n")

    # charts for the README
    DOCS.mkdir(exist_ok=True)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True,
                                   gridspec_kw={"height_ratios": [3, 1]})
    for (name, r), color in zip(results.items(), ["C0", "C1", "C2"]):
        (1 + r["ret"]).cumprod().plot(ax=ax1, label=name, color=color)
        if name != "equal weight":
            r["exposure"].plot(ax=ax2, label=name, lw=1, color=color)
    ax1.set_title(f"Growth of $1, net of costs ({period})")
    ax1.legend()
    ax2.axhline(1, color="black", lw=0.8, ls="--")
    ax2.set_ylabel("Gross exposure")
    plt.tight_layout()
    plt.savefig(DOCS / "backtest.png", dpi=130)

    fig, ax = plt.subplots(figsize=(11, 3.5))
    for name, r in results.items():
        eq = (1 + r["ret"]).cumprod()
        (eq / eq.cummax() - 1).plot(ax=ax, label=name, lw=1)
    ax.set_title("Drawdown")
    ax.legend()
    plt.tight_layout()
    plt.savefig(DOCS / "drawdown.png", dpi=130)
    print(f"charts saved to {DOCS}")
