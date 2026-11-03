"""Walk-forward vol forecasting across the universe.

Writes reports/forecast_scores.md and reports/oos_preds.parquet
(the out-of-sample forecasts the backtest uses for sizing).

usage: python scripts/run_forecast.py
"""

from voltrade import config, metrics
from voltrade.data import load_prices
from voltrade.features import make_dataset
from voltrade.models import walk_forward_predict
from voltrade.validation import describe_splits

BASELINE = "rolling_mean"

if __name__ == "__main__":
    X, y = make_dataset(load_prices())
    print(f"{len(X):,} stock-days, {X.index.get_level_values('ticker').nunique()} tickers")
    print("\n".join(describe_splits(X.index)))

    oos = walk_forward_predict(X, y)
    names = [c for c in oos.columns if c not in ("y", "fold")]

    overall = metrics.forecast_report(oos["y"], {n: oos[n] for n in names}, BASELINE)
    by_fold = oos.groupby("fold").apply(
        lambda d: metrics.forecast_report(d["y"], {n: d[n] for n in names}, BASELINE)["rmse"]
    ).unstack()[overall.index]

    best = overall.index[0]
    cut = 1 - overall.loc[best, "rmse"] / overall.loc[BASELINE, "rmse"]
    summary = f"best model: {best}, RMSE {cut:.1%} lower than the {BASELINE} baseline"

    config.REPORT_DIR.mkdir(exist_ok=True)
    oos.to_parquet(config.REPORT_DIR / "oos_preds.parquet")
    with open(config.REPORT_DIR / "forecast_scores.md", "w") as f:
        f.write("## Out-of-sample forecast scores (log vol)\n\n")
        f.write(overall.round(4).to_markdown() + "\n\n")
        f.write("## RMSE by fold\n\n" + by_fold.round(4).to_markdown() + "\n\n")
        f.write(summary + "\n")

    print(overall.round(4).to_markdown())
    print(by_fold.round(4).to_markdown())
    print(summary)
