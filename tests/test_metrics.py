import numpy as np
import pandas as pd
import pytest

from voltrade import metrics


def test_perfect_forecast_scores_zero():
    y = np.log(np.array([0.1, 0.2, 0.3]))
    assert metrics.rmse(y, y) == 0
    assert metrics.mae(y, y) == 0
    assert metrics.qlike(y, y) == pytest.approx(0)


def test_qlike_punishes_under_prediction_more():
    y = np.log(np.full(10, 0.20))
    under = metrics.qlike(y, np.log(np.full(10, 0.15)))
    over = metrics.qlike(y, np.log(np.full(10, 0.25)))
    assert under > over


def test_r2_vs_baseline():
    y = np.array([1.0, 2.0, 3.0])
    assert metrics.r2_vs(y, y, y + 1) == 1.0
    assert metrics.r2_vs(y, y + 1, y + 1) == 0.0


def test_max_drawdown():
    # up 10%, down 50%, up 20%: peak 1.1, trough 0.55
    r = pd.Series([0.10, -0.50, 0.20])
    assert metrics.max_drawdown(r) == pytest.approx(-0.5)


def test_sharpe_scale_invariant():
    rng = np.random.default_rng(1)
    r = pd.Series(rng.normal(0.0005, 0.01, 1000))
    assert metrics.sharpe(r) == pytest.approx(metrics.sharpe(2 * r))
