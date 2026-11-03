import numpy as np

from voltrade.features import build_features, build_target, make_dataset


def test_features_have_no_lookahead(fake_px):
    """Changing prices after day t must not change any feature at day t."""
    cut = fake_px.index[200]
    before = build_features(fake_px).xs(cut, level="date")

    shocked = fake_px.copy()
    shocked.loc[shocked.index > cut] *= 3.0
    after = build_features(shocked).xs(cut, level="date")

    # mkt_vol and the rest must all be identical
    np.testing.assert_allclose(before.values, after.values)


def test_target_looks_forward(fake_px):
    """The target at t must change when future prices change."""
    cut = fake_px.index[200]
    y0 = build_target(fake_px, horizon=20).xs(cut, level="date")

    shocked = fake_px.copy()
    shocked.loc[shocked.index[205], "Close"] *= 1.2
    y1 = build_target(shocked, horizon=20).xs(cut, level="date")

    assert not np.allclose(y0.values, y1.values)


def test_dataset_is_aligned_and_clean(fake_px):
    X, y = make_dataset(fake_px, horizon=20)
    assert X.index.equals(y.index)
    assert not X.isna().any().any()
    assert np.isfinite(y).all()
    # last 20 days have no target, so they are dropped
    assert X.index.get_level_values("date").max() < fake_px.index[-20]
