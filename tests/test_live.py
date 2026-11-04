import pandas as pd
import pytest

from voltrade.live import DryRunBroker, plan_orders, rebalance


def test_plan_orders_deltas_and_sells_first():
    targets = pd.Series({"AAA": 0.5, "BBB": 0.5})
    positions = {"AAA": 70_000.0, "CCC": 10_000.0}  # CCC is no longer wanted
    orders = plan_orders(targets, equity=100_000, positions=positions)

    assert [o[1] for o in orders] == ["sell", "sell", "buy"]
    as_dict = {(s, side): n for s, side, n in orders}
    assert as_dict[("AAA", "sell")] == pytest.approx(20_000)
    assert as_dict[("CCC", "sell")] == pytest.approx(10_000)
    assert as_dict[("BBB", "buy")] == pytest.approx(50_000)


def test_tiny_trades_are_skipped():
    targets = pd.Series({"AAA": 0.5})
    orders = plan_orders(targets, equity=100_000, positions={"AAA": 49_990.0})
    assert orders == []


def test_dry_run_sends_nothing_real():
    broker = DryRunBroker(equity=10_000)
    results, summary = rebalance(broker, pd.Series({"AAA": 0.6, "BBB": 0.6}))
    assert summary["n_orders"] == 2
    assert summary["traded_notional"] == pytest.approx(12_000)
    assert all(r.status == "dry_run" for r in results)
