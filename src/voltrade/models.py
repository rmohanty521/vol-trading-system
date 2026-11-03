"""Vol forecasting: baselines and scikit-learn models.

Everything predicts LOG vol. Vol is right-skewed and strictly positive,
so logs make the target closer to normal and rule out negative forecasts.
"""

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

from voltrade.validation import walk_forward_splits

# strictly positive, skewed columns that behave better in logs
LOG_COLS = ["vol5", "vol20", "vol60", "ewm_vol", "vol_of_vol", "hl_vol", "volume_ratio", "mkt_vol"]


def baselines(X):
    """Rule-based forecasts that need no training. Returns log-vol columns."""
    roll = X.groupby(level="ticker")["vol20"].transform(lambda s: s.rolling(20).mean())
    return pd.DataFrame(
        {
            "naive": np.log(X["vol20"]),  # next 20 days look like the last 20
            "rolling_mean": np.log(roll),  # average of the last 20 days' vol20
            "ewma": np.log(X["ewm_vol"]),  # what most practitioners start from
        },
        index=X.index,
    )


def _log_then_scale(columns):
    log_cols = [c for c in LOG_COLS if c in columns]
    rest = [c for c in columns if c not in log_cols]
    return ColumnTransformer(
        [
            ("log", FunctionTransformer(np.log), log_cols),
            ("raw", "passthrough", rest),
        ]
    )


def make_models(columns):
    return {
        "ridge": make_pipeline(_log_then_scale(columns), StandardScaler(), Ridge(alpha=10.0)),
        "hgb": HistGradientBoostingRegressor(
            max_depth=4, learning_rate=0.05, max_iter=300, min_samples_leaf=200, random_state=0
        ),
    }


def walk_forward_predict(X, y, **split_kw):
    """Out-of-sample predictions for every row in a test fold.

    Returns a frame with a `fold` column, `y` (realized log vol), one column
    per baseline and one per model, indexed like X.
    """
    base = baselines(X)
    parts = []
    for fold, (tr, te) in enumerate(walk_forward_splits(X.index, **split_kw)):
        out = base.iloc[te].copy()
        out["y"] = y.iloc[te].values
        out["fold"] = fold
        for name, model in make_models(X.columns).items():
            model.fit(X.iloc[tr], y.iloc[tr])
            out[name] = model.predict(X.iloc[te])
        parts.append(out)
    return pd.concat(parts).dropna()
