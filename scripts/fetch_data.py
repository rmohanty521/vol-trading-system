"""Download and cache prices for the universe.

usage: python scripts/fetch_data.py [--refresh]
"""

import sys

from voltrade import config
from voltrade.data import load_prices

if __name__ == "__main__":
    px = load_prices(refresh="--refresh" in sys.argv)
    close = px["Close"]
    print(f"{close.shape[1]} tickers, {len(close)} days")
    print(f"{close.index[0].date()} to {close.index[-1].date()}")
    print(f"cached in {config.DATA_DIR}")
