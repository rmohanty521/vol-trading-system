"""Daily backtest engine with weight drift and transaction costs.

Target weights are decided at the close of a rebalance date and held from
the next day on. Between rebalances, weights drift with prices; anything
not invested sits in cash at 0%. Costs are charged on traded notional.
"""

import numpy as np
import pandas as pd

from voltrade import config


def run(target_weights, ret, cost_bps=None):
    """Simulate a strategy.

    target_weights: frame indexed by rebalance dates, columns = tickers.
    ret: daily simple returns, wide frame covering the backtest window.
    Returns a frame with daily `ret` (net), `gross_ret`, `turnover`, `exposure`.
    """
    cost = (config.COST_BPS if cost_bps is None else cost_bps) / 1e4
    ret = ret.loc[target_weights.index[0]:, target_weights.columns].fillna(0.0)
    targets = target_weights.reindex(columns=ret.columns).fillna(0.0)

    w = np.zeros(ret.shape[1])
    out = np.zeros((len(ret), 4))

    for i, (day, r) in enumerate(zip(ret.index, ret.values)):
        # 1. earn today's return on yesterday's holdings
        gross = float(w @ r)
        # 2. weights drift: each holding grows with its stock, the book with the total
        w = w * (1 + r) / (1 + gross)

        # 3. trade to target at today's close if this is a rebalance date
        turnover = 0.0
        if day in targets.index:
            new_w = targets.loc[day].values
            turnover = float(np.abs(new_w - w).sum())
            w = new_w

        net = (1 + gross) * (1 - turnover * cost) - 1
        out[i] = [net, gross, turnover, np.abs(w).sum()]

    return pd.DataFrame(out, index=ret.index, columns=["ret", "gross_ret", "turnover", "exposure"])
