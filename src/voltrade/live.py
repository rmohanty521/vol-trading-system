"""Live rebalancing: forecast today's vols, size the book, send orders.

Two brokers share one interface:
- DryRunBroker: logs what it would trade, touches nothing. The default.
- AlpacaBroker: Alpaca PAPER account only. Keys come from the environment.
"""

import os
import time
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from voltrade import config, sizing
from voltrade.data import load_prices, returns
from voltrade.features import build_features, make_dataset
from voltrade.models import make_models

MIN_TRADE_USD = 25.0  # skip tiny rebalances: not worth the spread


@dataclass
class OrderResult:
    symbol: str
    side: str
    notional: float
    order_id: str = ""
    status: str = "dry_run"
    latency_ms: float = 0.0  # submit call -> broker acknowledgement
    filled: bool = False
    extra: dict = field(default_factory=dict)


# ---------- signal ----------


def compute_targets(model_name="ridge", refresh=True):
    """Train on all labeled history, forecast the latest day, return target weights.

    Returns (weights Series indexed by ticker, forecast vols Series, as-of date).
    """
    px = load_prices(refresh=refresh)
    X, y = make_dataset(px)
    model = make_models(X.columns)[model_name].fit(X, y)

    # today's features exist even though today's target doesn't yet
    feats = build_features(px).replace([np.inf, -np.inf], np.nan).dropna()
    asof = feats.index.get_level_values("date").max()
    today = feats.xs(asof, level="date")
    fc_vol = pd.Series(np.exp(model.predict(today)), index=today.index)

    vol_frame = fc_vol.to_frame().T.set_axis([asof])
    w = sizing.vol_target_weights(vol_frame, returns(px["Close"]), [asof])
    return w.iloc[0], fc_vol, asof


# ---------- brokers ----------


class DryRunBroker:
    def __init__(self, equity=100_000.0):
        self._equity = equity
        self.orders = []

    def is_open(self):
        return True

    def equity(self):
        return self._equity

    def last_equity(self):
        return self._equity

    def positions(self):
        return {}

    def submit(self, symbol, side, notional):
        res = OrderResult(symbol, side, round(notional, 2))
        self.orders.append(res)
        return res

    def check_fill(self, res):
        return res


class AlpacaBroker:
    """Alpaca paper trading. paper=True is hard-coded on purpose."""

    def __init__(self):
        from alpaca.trading.client import TradingClient

        key, secret = os.environ.get("ALPACA_API_KEY"), os.environ.get("ALPACA_SECRET_KEY")
        if not key or not secret:
            raise RuntimeError("set ALPACA_API_KEY and ALPACA_SECRET_KEY (paper keys)")
        self.client = TradingClient(key, secret, paper=True)

    def is_open(self):
        return self.client.get_clock().is_open

    def equity(self):
        return float(self.client.get_account().equity)

    def last_equity(self):
        """Equity at the previous close, for daily P&L."""
        return float(self.client.get_account().last_equity)

    def positions(self):
        return {p.symbol: float(p.market_value) for p in self.client.get_all_positions()}

    def submit(self, symbol, side, notional):
        from alpaca.trading.enums import OrderSide, TimeInForce
        from alpaca.trading.requests import MarketOrderRequest

        req = MarketOrderRequest(
            symbol=symbol,
            notional=round(notional, 2),
            side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
        )
        t0 = time.perf_counter()
        order = self.client.submit_order(order_data=req)
        latency = (time.perf_counter() - t0) * 1000
        return OrderResult(symbol, side, round(notional, 2), str(order.id),
                           str(order.status.value), latency)

    def check_fill(self, res):
        order = self.client.get_order_by_id(res.order_id)
        res.status = str(order.status.value)
        res.filled = res.status == "filled"
        if order.filled_avg_price:
            res.extra["fill_price"] = float(order.filled_avg_price)
        return res


# ---------- rebalance ----------


def plan_orders(targets, equity, positions, min_trade=MIN_TRADE_USD):
    """Dollar trades needed to move from current positions to target weights.

    Sells come first so they free up buying power for the buys.
    """
    symbols = sorted(set(targets.index) | set(positions))
    want = targets.reindex(symbols).fillna(0.0) * equity
    have = pd.Series(positions, dtype=float).reindex(symbols).fillna(0.0)
    delta = (want - have)[lambda d: d.abs() >= min_trade]

    sells = [(s, "sell", -v) for s, v in delta[delta < 0].items()]
    buys = [(s, "buy", v) for s, v in delta[delta > 0].items()]
    return sells + buys


def rebalance(broker, targets, fill_wait_s=30):
    """Send orders and return (results, summary dict)."""
    dry = isinstance(broker, DryRunBroker)
    equity = broker.equity()
    orders = plan_orders(targets, equity, broker.positions())
    results = [broker.submit(s, side, n) for s, side, n in orders]

    if results and not dry:
        time.sleep(fill_wait_s)  # market orders usually fill in well under this
        results = [broker.check_fill(r) for r in results]

    lat = [r.latency_ms for r in results if r.latency_ms]
    summary = {
        "equity": equity,
        "n_orders": len(results),
        "traded_notional": sum(r.notional for r in results),
        "gross_target": float(targets.sum()),
        "fill_rate": None if dry or not results else sum(r.filled for r in results) / len(results),
        "median_latency_ms": float(np.median(lat)) if lat else None,
    }
    return results, summary
