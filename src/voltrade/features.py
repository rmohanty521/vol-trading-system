"""Per-stock volatility features and the forward-looking target.

Every feature at date t uses data through the close of t only.
The target is the one place a negative shift is allowed: it is the
realized vol over the next HORIZON days, which is what we try to predict.
"""

import numpy as np
import pandas as pd

from voltrade import config
from voltrade.data import returns

ANN = np.sqrt(252)


def _rv(ret, window):
    return ret.rolling(window).std() * ANN


def build_features(px):
    """Return a long frame indexed by (date, ticker) with one column per feature."""
    close, high, low, vol = px["Close"], px["High"], px["Low"], px["Volume"]
    ret = returns(close)

    vol20 = _rv(ret, 20)
    # market-wide vol: average vol20 across the universe, same value for every stock
    mkt_vol = vol20.mean(axis=1)

    feats = {
        "vol5": _rv(ret, 5),
        "vol20": vol20,
        "vol60": _rv(ret, 60),
        "ewm_vol": ret.ewm(span=20).std() * ANN,
        "vol_of_vol": vol20.rolling(20).std(),
        "abs_ret": ret.abs(),
        "neg_flag": (ret < 0).astype(float).where(ret.notna()),
        # Parkinson high-low estimator, a more efficient daily vol proxy
        "hl_vol": np.sqrt((np.log(high / low) ** 2) / (4 * np.log(2))).rolling(5).mean() * ANN,
        "volume_ratio": vol / vol.rolling(20).mean(),
        "mkt_vol": pd.DataFrame({t: mkt_vol for t in close.columns}),
    }

    long = pd.concat({k: v.stack() for k, v in feats.items()}, axis=1)
    long.index.names = ["date", "ticker"]
    return long


def build_target(px, horizon=None):
    """Log realized vol over the next `horizon` days, indexed by (date, ticker)."""
    horizon = horizon or config.HORIZON
    ret = returns(px["Close"])
    fwd = _rv(ret, horizon).shift(-horizon)
    y = np.log(fwd).stack()
    y.index.names = ["date", "ticker"]
    return y.rename("target")


def make_dataset(px, horizon=None):
    """Aligned (X, y), rows with any missing value dropped, sorted by date."""
    X = build_features(px)
    y = build_target(px, horizon)
    data = X.join(y, how="inner").replace([np.inf, -np.inf], np.nan).dropna()
    data = data.sort_index(level=["date", "ticker"])
    return data.drop(columns="target"), data["target"]
