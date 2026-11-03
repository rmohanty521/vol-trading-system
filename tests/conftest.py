import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def fake_px():
    """Synthetic OHLCV for 3 tickers over 300 days, no network needed."""
    rng = np.random.default_rng(0)
    dates = pd.bdate_range("2022-01-03", periods=300)
    tickers = ["AAA", "BBB", "CCC"]
    ret = rng.normal(0, 0.015, (300, 3))
    close = pd.DataFrame(100 * np.exp(np.cumsum(ret, axis=0)), index=dates, columns=tickers)
    spread = np.abs(rng.normal(0, 0.01, (300, 3)))
    frames = {
        "Open": close.shift(1).fillna(close),
        "High": close * (1 + spread),
        "Low": close * (1 - spread),
        "Close": close,
        "Volume": pd.DataFrame(rng.integers(1e6, 5e6, (300, 3)), index=dates, columns=tickers),
    }
    return pd.concat(frames, axis=1)
