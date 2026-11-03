"""Walk-forward splits for panel data.

Splits are made on dates, not rows, so every stock on a given day lands in
the same fold. A gap of HORIZON days sits between train and test: the target
looks HORIZON days ahead, so without it the last training labels would
overlap the test period and leak the answer.
"""

import numpy as np
from sklearn.model_selection import TimeSeriesSplit

from voltrade import config


def walk_forward_splits(index, n_splits=None, gap=None):
    """Yield (train_rows, test_rows) integer arrays for a (date, ticker) index.

    Expanding window: each fold trains on everything before its test block.
    """
    n_splits = n_splits or config.N_SPLITS
    gap = config.HORIZON if gap is None else gap

    dates = index.get_level_values("date")
    uniq = np.unique(dates)
    tscv = TimeSeriesSplit(n_splits=n_splits, gap=gap)

    for train_d, test_d in tscv.split(uniq):
        train_rows = np.flatnonzero(dates.isin(uniq[train_d]))
        test_rows = np.flatnonzero(dates.isin(uniq[test_d]))
        yield train_rows, test_rows


def describe_splits(index, **kw):
    """Human-readable date ranges per fold."""
    dates = index.get_level_values("date")
    out = []
    for i, (tr, te) in enumerate(walk_forward_splits(index, **kw)):
        out.append(
            f"fold {i}: train {dates[tr].min().date()} to {dates[tr].max().date()}"
            f" | test {dates[te].min().date()} to {dates[te].max().date()}"
        )
    return out
