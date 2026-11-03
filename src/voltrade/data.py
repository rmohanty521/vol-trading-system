"""Download daily OHLCV for the universe and cache it locally as parquet."""

import warnings

import pandas as pd
import yfinance as yf

from voltrade import config

FIELDS = ["Open", "High", "Low", "Close", "Volume"]


def _cache_path(start, end):
    return config.DATA_DIR / f"prices_{start}_{end or 'latest'}.parquet"


def download(tickers, start, end=None):
    """Fetch adjusted daily bars. Returns a frame with (field, ticker) columns."""
    # yfinance trips pandas deprecation warnings internally; not ours to fix
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        raw = yf.download(
            tickers, start=start, end=end, auto_adjust=True, progress=False, threads=True
        )
    raw = raw[FIELDS]
    raw.index = pd.to_datetime(raw.index).tz_localize(None)
    raw.index.name = "date"
    return raw.sort_index()


def load_prices(tickers=None, start=None, end=None, refresh=False):
    """Load prices from cache, downloading if missing or refresh=True.

    Drops tickers with more than 5% missing closes, and drops dates where
    every ticker is missing (exchange holidays that slip in).
    """
    tickers = tickers or config.UNIVERSE
    start = start or config.START
    end = end if end is not None else config.END

    path = _cache_path(start, end)
    if path.exists() and not refresh:
        px = pd.read_parquet(path)
    else:
        px = download(tickers, start, end)
        config.DATA_DIR.mkdir(exist_ok=True)
        px.to_parquet(path)

    px = px.loc[:, px.columns.get_level_values(1).isin(tickers)]
    close = px["Close"]
    keep = close.columns[close.isna().mean() <= 0.05]
    dropped = sorted(set(tickers) - set(keep))
    if dropped:
        print(f"dropping tickers with too much missing data: {dropped}")
    px = px.loc[:, px.columns.get_level_values(1).isin(keep)]
    return px.dropna(how="all")


def returns(close):
    """Simple daily returns. First row is NaN by construction."""
    return close.pct_change(fill_method=None)
