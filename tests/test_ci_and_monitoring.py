import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from ci_run import decide  # noqa: E402

from voltrade.monitoring import Metrics  # noqa: E402

NY = ZoneInfo("America/New_York")


@pytest.mark.parametrize(
    "when, expected",
    [
        ("2026-11-06 15:31", ["--paper"]),  # Friday 15:31: rebalance
        ("2026-11-04 15:31", ["--paper", "--pnl"]),  # Wednesday: P&L only
        ("2026-11-06 14:31", None),  # the cron that fired an hour early
        ("2026-11-06 16:31", None),  # the cron that fired an hour late
        ("2026-11-07 15:31", None),  # Saturday
    ],
)
def test_decide(when, expected):
    now = datetime.fromisoformat(when).replace(tzinfo=NY)
    assert decide(now, []) == expected


def test_force_flags_override_window():
    sunday = datetime(2026, 11, 8, 3, 0, tzinfo=NY)
    assert decide(sunday, ["--force-rebalance"]) == ["--paper"]
    assert decide(sunday, ["--force-pnl"]) == ["--paper", "--pnl"]


def test_http_backend_buffers_and_summarizes(monkeypatch):
    monkeypatch.delenv("DD_AGENT_HOST", raising=False)
    monkeypatch.setenv("DD_API_KEY", "test")
    m = Metrics()
    sent = []
    monkeypatch.setattr(m, "_post", lambda path, body: sent.append((path, body)))

    m.gauge("portfolio.equity", 100_000)
    for v in [100, 200, 300]:
        m.histogram("order.latency_ms", v)
    m.flush()

    (path, body), = sent
    assert path == "/api/v2/series"
    got = {s["metric"]: s["points"][0]["value"] for s in body["series"]}
    assert got["voltrade.portfolio.equity"] == 100_000
    assert got["voltrade.order.latency_ms.median"] == 200
    assert got["voltrade.order.latency_ms.count"] == 3
