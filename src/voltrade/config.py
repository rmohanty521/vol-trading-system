"""Project-wide settings. Everything tunable lives here so experiments are reproducible."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
REPORT_DIR = ROOT / "reports"

# 50 large-cap US equities across all 11 sectors.
# Caveat: these were picked because they are large today (survivorship bias).
UNIVERSE = [
    # tech
    "AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "CSCO", "ADBE", "CRM", "INTC", "QCOM",
    # communication
    "GOOGL", "META", "NFLX", "DIS", "VZ",
    # consumer discretionary
    "AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX",
    # consumer staples
    "PG", "KO", "PEP", "WMT", "COST",
    # health care
    "JNJ", "UNH", "LLY", "PFE", "MRK", "ABT",
    # financials
    "JPM", "BAC", "GS", "MS", "V", "MA",
    # industrials
    "CAT", "HON", "UNP", "GE",
    # energy
    "XOM", "CVX", "COP",
    # utilities
    "NEE", "DUK",
    # real estate
    "AMT", "PLD",
    # materials
    "LIN",
]

# 5 years of daily data for the backtest
START = "2021-11-01"
END = None  # None = up to today

# forecasting
HORIZON = 20  # predict realized vol over the next 20 trading days
N_SPLITS = 5  # walk-forward folds

# sizing
VOL_TARGET = 0.10  # annualized portfolio vol target
MAX_LEVERAGE = 1.5  # gross exposure cap
COST_BPS = 5  # transaction cost per unit of turnover, in basis points
REBALANCE = "W-FRI"  # rebalance weekly to keep turnover sane
