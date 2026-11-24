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


UTC = ZoneInfo("UTC")
EDT_CRON, EST_CRON = "30 19 * * 1-5", "30 20 * * 1-5"


@pytest.mark.parametrize(
    "started_utc, schedule, expected",
    [
        # real late starts from November (EST): GitHub ran them 4-8 hours late
        ("2026-11-21 01:38", EST_CRON, ["--paper"]),  # Friday's 15:30 run, started 20:38 NY
        ("2026-11-21 00:53", EDT_CRON, None),  # Friday's 14:30 run: the wrong cron in winter
        ("2026-11-24 04:54", EST_CRON, ["--paper", "--pnl"]),  # Monday, started 23:54 NY
        ("2026-11-24 04:21", EDT_CRON, None),
        # summer (EDT): the other cron is the real one
        ("2026-07-15 22:10", EDT_CRON, ["--paper", "--pnl"]),
        ("2026-07-15 23:05", EST_CRON, None),
        # on time still works
        ("2026-11-20 20:31", EST_CRON, ["--paper"]),
    ],
)
def test_decide_uses_scheduled_time_not_start_time(started_utc, schedule, expected):
    now = datetime.fromisoformat(started_utc).replace(tzinfo=UTC).astimezone(NY)
    assert decide(now, [], schedule) == expected


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
