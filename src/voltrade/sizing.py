"""Turn per-stock vol estimates into portfolio weights.

Two steps on each rebalance date:
1. Inverse-vol weights, so each stock contributes similar risk.
2. Scale the whole book so its estimated vol hits VOL_TARGET, using the
   stock vols plus trailing correlations. Gross exposure is capped.
"""

import numpy as np
import pandas as pd

from voltrade import config


def rebalance_dates(index, freq=None):
    """Last trading day of each period (e.g. each Friday) within `index`."""
    freq = freq or config.REBALANCE
    s = pd.Series(index, index=index)
    return pd.DatetimeIndex(s.groupby(pd.Grouper(freq=freq)).last().dropna().values)


def equal_weights(tickers, dates):
    n = len(tickers)
    return pd.DataFrame(1.0 / n, index=dates, columns=tickers)


def vol_target_weights(vol, ret, dates, target=None, max_lev=None, corr_window=60):
    """Weights per rebalance date.

    vol: annualized vol estimate per (date, ticker), wide frame. Must be
         known at the close of each date (forecast or trailing realized).
    ret: daily returns, wide frame, used only for trailing correlations.
    """
    target = target or config.VOL_TARGET
    max_lev = max_lev or config.MAX_LEVERAGE

    rows = {}
    for d in dates:
        sig = vol.loc[d].dropna()
        hist = ret.loc[:d, sig.index].tail(corr_window)
        if len(sig) < 2 or len(hist) < corr_window:
            continue

        w = 1.0 / sig
        w = w / w.sum()

        corr = hist.corr().fillna(0).values
        cov = np.outer(sig, sig) * corr
        port_vol = float(np.sqrt(w.values @ cov @ w.values))

        scale = min(target / port_vol, max_lev)
        rows[d] = w * scale

    return pd.DataFrame(rows).T.reindex(columns=vol.columns).fillna(0.0)
