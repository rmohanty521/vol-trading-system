import numpy as np
import pandas as pd
import pytest

from voltrade import backtest, sizing


@pytest.fixture
def two_assets():
    dates = pd.bdate_range("2024-01-01", periods=5)
    ret = pd.DataFrame({"A": [0.0, 0.10, -0.05, 0.02, 0.0], "B": [0.0] * 5}, index=dates)
    return dates, ret


def test_weights_apply_from_next_day(two_assets):
    """A position set at day 0's close earns day 1's return, not day 0's."""
    dates, ret = two_assets
    ret.iloc[0, 0] = 0.50  # a huge day-0 move that must NOT be captured
    tw = pd.DataFrame({"A": [1.0], "B": [0.0]}, index=dates[:1])
    res = backtest.run(tw, ret, cost_bps=0)
    assert res["ret"].iloc[0] == 0
    assert res["ret"].iloc[1] == pytest.approx(0.10)


def test_buy_and_hold_matches_asset(two_assets):
    dates, ret = two_assets
    tw = pd.DataFrame({"A": [1.0], "B": [0.0]}, index=dates[:1])
    res = backtest.run(tw, ret, cost_bps=0)
    total = (1 + res["ret"]).prod() - 1
    assert total == pytest.approx((1 + ret["A"].iloc[1:]).prod() - 1)


def test_costs_charged_on_turnover(two_assets):
    dates, ret = two_assets
    tw = pd.DataFrame({"A": [1.0], "B": [0.0]}, index=dates[:1])
    res = backtest.run(tw, ret, cost_bps=10)
    # initial buy: turnover 1.0, cost 10 bp
    assert res["turnover"].iloc[0] == pytest.approx(1.0)
    assert res["ret"].iloc[0] == pytest.approx(-0.001)


def test_vol_target_scales_down_in_high_vol():
    rng = np.random.default_rng(0)
    dates = pd.bdate_range("2024-01-01", periods=100)
    ret = pd.DataFrame(rng.normal(0, 0.01, (100, 3)), index=dates, columns=list("XYZ"))
    calm = pd.DataFrame(0.10, index=dates, columns=ret.columns)
    wild = calm * 4

    d = dates[-1:]
    w_calm = sizing.vol_target_weights(calm, ret, d, target=0.10, max_lev=10)
    w_wild = sizing.vol_target_weights(wild, ret, d, target=0.10, max_lev=10)
    assert w_wild.sum(axis=1).iloc[0] == pytest.approx(w_calm.sum(axis=1).iloc[0] / 4)


def test_leverage_cap():
    dates = pd.bdate_range("2024-01-01", periods=100)
    ret = pd.DataFrame(np.random.default_rng(1).normal(0, 0.001, (100, 2)), index=dates, columns=["X", "Y"])
    tiny_vol = pd.DataFrame(0.01, index=dates, columns=ret.columns)
    w = sizing.vol_target_weights(tiny_vol, ret, dates[-1:], target=0.10, max_lev=1.5)
    assert w.sum(axis=1).iloc[0] == pytest.approx(1.5)
