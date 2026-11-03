import numpy as np

from voltrade.features import make_dataset
from voltrade.validation import walk_forward_splits


def test_splits_are_walk_forward_with_gap(fake_px):
    X, _ = make_dataset(fake_px, horizon=20)
    dates = X.index.get_level_values("date")
    uniq = np.unique(dates)

    folds = list(walk_forward_splits(X.index, n_splits=3, gap=20))
    assert len(folds) == 3
    for tr, te in folds:
        last_train, first_test = dates[tr].max(), dates[te].min()
        # at least `gap` trading days between train and test
        n_between = ((uniq > last_train) & (uniq < first_test)).sum()
        assert n_between >= 20
        # no date is in both sets, so no stock leaks across the split
        assert not set(dates[tr]) & set(dates[te])


def test_training_window_expands(fake_px):
    X, _ = make_dataset(fake_px, horizon=20)
    sizes = [len(tr) for tr, _ in walk_forward_splits(X.index, n_splits=3, gap=20)]
    assert sizes == sorted(sizes) and sizes[0] < sizes[-1]
