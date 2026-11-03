# vol-trading-system

A volatility-aware trading system. A scikit-learn model forecasts each stock's volatility,
and the forecasts size positions so the portfolio runs at a fixed risk level.

Python · pandas · scikit-learn · Alpaca API · Datadog

## Pipeline

1. **Data**: 5 years of daily prices for 50 large-cap US equities
2. **Forecast**: predict each stock's next-20-day realized vol, validated walk-forward
3. **Size**: inverse-vol weights, scaled to a 10% portfolio vol target
4. **Backtest**: compare against equal weight, net of transaction costs
5. **Trade**: paper-trade on Alpaca, monitored with Datadog

## Setup

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

All settings are in `src/voltrade/config.py`.
