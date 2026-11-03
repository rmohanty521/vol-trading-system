"""Forecast-error and portfolio-performance metrics."""

import numpy as np
import pandas as pd

# ---------- forecast metrics (inputs are log vol) ----------


def rmse(y_true, y_pred):
    return float(np.sqrt(np.mean((np.asarray(y_true) - np.asarray(y_pred)) ** 2)))


def mae(y_true, y_pred):
    return float(np.mean(np.abs(np.asarray(y_true) - np.asarray(y_pred))))


def qlike(y_true, y_pred):
    """QLIKE loss on variance, the standard vol-forecast loss.

    r/h - log(r/h) - 1, where r is realized variance and h the forecast.
    Zero for a perfect forecast; under-prediction is punished harder.
    """
    ratio = np.exp(2 * (np.asarray(y_true) - np.asarray(y_pred)))
    return float(np.mean(ratio - np.log(ratio) - 1))


def r2_vs(y_true, y_pred, y_base):
    """Out-of-sample R^2 against a baseline: 1 - MSE_model / MSE_baseline."""
    y_true = np.asarray(y_true)
    mse_m = np.mean((y_true - np.asarray(y_pred)) ** 2)
    mse_b = np.mean((y_true - np.asarray(y_base)) ** 2)
    return float(1 - mse_m / mse_b)


def forecast_report(y_true, preds, baseline):
    """One row per model in `preds` (dict name -> predictions)."""
    rows = {
        name: {
            "rmse": rmse(y_true, p),
            "mae": mae(y_true, p),
            "qlike": qlike(y_true, p),
            f"r2_vs_{baseline}": r2_vs(y_true, p, preds[baseline]),
        }
        for name, p in preds.items()
    }
    return pd.DataFrame(rows).T.sort_values("rmse")


# ---------- portfolio metrics (inputs are daily simple returns) ----------


def ann_return(r):
    r = pd.Series(r).dropna()
    return float((1 + r).prod() ** (252 / len(r)) - 1)


def ann_vol(r):
    return float(pd.Series(r).std() * np.sqrt(252))


def sharpe(r):
    """Annualized Sharpe with a zero risk-free rate."""
    r = pd.Series(r).dropna()
    return float(r.mean() / r.std() * np.sqrt(252))


def max_drawdown(r):
    eq = (1 + pd.Series(r).dropna()).cumprod()
    return float((eq / eq.cummax() - 1).min())


def perf_stats(r):
    return {
        "Total ret": float((1 + pd.Series(r).dropna()).prod() - 1),
        "Ann. ret": ann_return(r),
        "Ann. vol": ann_vol(r),
        "Sharpe": sharpe(r),
        "MaxDD": max_drawdown(r),
    }
