"""Datadog metrics.

Three backends, picked from the environment:
- DD_AGENT_HOST set: DogStatsD to a local agent (the docker-compose deploy).
- DD_API_KEY set:    batched straight to Datadog's HTTP API (GitHub Actions,
                     where there is no agent). Call flush() before exiting.
- neither:           print to stdout, so the bot runs the same without Datadog.

Metrics (all prefixed voltrade.):
    order.latency_ms        histogram  submit -> broker ack, per order
                                       (.median / .avg / .max / .count)
    order.submitted         count
    order.filled            count
    rebalance.fill_rate     gauge      filled / submitted for the last rebalance
    rebalance.traded_usd    gauge
    portfolio.equity        gauge
    portfolio.pnl_daily     gauge      equity - previous close equity
    portfolio.gross_target  gauge      target gross exposure (leverage)
    forecast.vol            gauge      per-ticker forecast vol, tagged ticker:XYZ
"""

import json
import os
import statistics
import time
import urllib.request
from collections import defaultdict

COUNT, GAUGE = 1, 3  # Datadog v2 series metric types


class Metrics:
    def __init__(self, prefix="voltrade", tags=None):
        self.prefix = prefix
        self.tags = list(tags or []) + [f"env:{os.environ.get('VOLTRADE_ENV', 'dev')}"]

        if os.environ.get("DD_AGENT_HOST"):
            self.backend = "agent"
            from datadog import initialize, statsd

            initialize(
                statsd_host=os.environ["DD_AGENT_HOST"],
                statsd_port=int(os.environ.get("DD_DOGSTATSD_PORT", 8125)),
            )
            self._statsd = statsd
        elif os.environ.get("DD_API_KEY"):
            self.backend = "http"
            self._api = f"https://api.{os.environ.get('DD_SITE', 'datadoghq.com')}"
            self._series = []
            self._hist = defaultdict(list)  # (name, tags) -> values, summarized on flush
        else:
            self.backend = "print"

    # ---- primitives ----

    def _full(self, name, tags):
        return f"{self.prefix}.{name}", self.tags + list(tags or [])

    def _point(self, mtype, name, value, tags):
        self._series.append({
            "metric": name,
            "type": mtype,
            "points": [{"timestamp": int(time.time()), "value": float(value)}],
            "tags": tags,
        })

    def gauge(self, name, value, tags=None):
        if value is None:
            return
        name, tags = self._full(name, tags)
        if self.backend == "agent":
            self._statsd.gauge(name, value, tags=tags)
        elif self.backend == "http":
            self._point(GAUGE, name, value, tags)
        else:
            print(f"[metric] gauge {name}={value} {tags}")

    def count(self, name, value=1, tags=None):
        name, tags = self._full(name, tags)
        if self.backend == "agent":
            self._statsd.increment(name, value, tags=tags)
        elif self.backend == "http":
            self._point(COUNT, name, value, tags)
        else:
            print(f"[metric] count {name}={value} {tags}")

    def histogram(self, name, value, tags=None):
        """Agent mode: native histogram. HTTP mode: summarized per tag set on flush,
        using the same .median/.avg/.max/.count names DogStatsD produces."""
        name, tags = self._full(name, tags)
        if self.backend == "agent":
            self._statsd.histogram(name, value, tags=tags)
        elif self.backend == "http":
            self._hist[(name, tuple(tags))].append(value)
        else:
            print(f"[metric] histogram {name}={value} {tags}")

    def event(self, title, text, alert_type="info"):
        if self.backend == "agent":
            self._statsd.event(title, text, alert_type=alert_type, tags=self.tags)
        elif self.backend == "http":
            body = {"title": title, "text": text, "alert_type": alert_type, "tags": self.tags}
            self._post("/api/v1/events", body)
        else:
            print(f"[event] {alert_type}: {title} - {text}")

    def flush(self):
        """Send buffered HTTP-mode metrics. No-op for the other backends."""
        if self.backend != "http":
            return
        for (name, tags), vals in self._hist.items():
            tags = list(tags)
            self._point(GAUGE, f"{name}.median", statistics.median(vals), tags)
            self._point(GAUGE, f"{name}.avg", statistics.fmean(vals), tags)
            self._point(GAUGE, f"{name}.max", max(vals), tags)
            self._point(COUNT, f"{name}.count", len(vals), tags)
        self._hist.clear()
        if self._series:
            self._post("/api/v2/series", {"series": self._series})
            print(f"sent {len(self._series)} metric series to Datadog")
            self._series = []

    def _post(self, path, body):
        req = urllib.request.Request(
            self._api + path,
            data=json.dumps(body).encode(),
            headers={"DD-API-KEY": os.environ["DD_API_KEY"], "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            if r.status >= 300:
                raise RuntimeError(f"Datadog {path} returned {r.status}")

    # ---- domain helpers ----

    def record_rebalance(self, results, summary):
        for r in results:
            t = [f"ticker:{r.symbol}", f"side:{r.side}"]
            self.count("order.submitted", tags=t)
            if r.filled:
                self.count("order.filled", tags=t)
            if r.latency_ms:
                # no ticker tag: we want one latency distribution across all orders
                self.histogram("order.latency_ms", r.latency_ms)
        self.gauge("rebalance.fill_rate", summary.get("fill_rate"))
        self.gauge("rebalance.traded_usd", summary.get("traded_notional"))
        self.gauge("portfolio.gross_target", summary.get("gross_target"))

    def record_portfolio(self, equity, last_equity):
        self.gauge("portfolio.equity", equity)
        if last_equity:
            self.gauge("portfolio.pnl_daily", equity - last_equity)

    def record_forecasts(self, fc_vol):
        for ticker, v in fc_vol.items():
            self.gauge("forecast.vol", float(v), tags=[f"ticker:{ticker}"])
