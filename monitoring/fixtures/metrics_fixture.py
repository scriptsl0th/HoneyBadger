#!/usr/bin/env python3
"""Synthetic Prometheus exporter for HoneyBadger - DEV/DEMO ONLY.

This module is never part of production. It exists so Grafana dashboards,
recording rules and alert thresholds can be exercised before the real backend
exporter (backend/metrics.py) is implemented.

It serves the metric contract documented in ../README.md on :9101/metrics using
only the Python standard library, and increments counters on every scrape so
rates, increases and time series panels render realistically.

Run (compose profile):   docker compose --profile fixtures up -d
Run (standalone):        python metrics_fixture.py
"""

from __future__ import annotations

import os
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, List, Tuple

HOST = os.environ.get("FIXTURE_HOST", "0.0.0.0")
PORT = int(os.environ.get("FIXTURE_PORT", "9101"))

# Must match the technique IDs allowed by backend/schemas.py EnrichedEvent.
TECHNIQUES = ["T1110", "T1110.004", "T1595", "T1190", "T1105", "T1059", "T1078"]
SEVERITIES = ["low", "medium", "high", "critical"]
SERVICES = ["ssh", "http"]
STAGES = ["geoip", "mitre", "credentials", "storage"]
BUCKETS: List[float] = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]

_lock = threading.Lock()
_boot = time.time()

# Counter state (monotonically increasing for the life of the process).
_events: Dict[Tuple[str, str, str], float] = {
    (svc, tech, sev): float(random.randint(0, 40))
    for svc in SERVICES
    for tech in TECHNIQUES
    for sev in SEVERITIES
}
_credentials: Dict[str, float] = {svc: float(random.randint(10, 60)) for svc in SERVICES}
_http: Dict[Tuple[str, str], float] = {
    (method, status): float(random.randint(0, 30))
    for method in ("GET", "POST", "HEAD", "PUT")
    for status in ("200", "301", "400", "401", "403", "404", "500")
}
_ssh_connections = float(random.randint(20, 80))
_ssh_handshakes = float(random.randint(10, 40))
_ssh_commands = float(random.randint(30, 120))
_payloads: Dict[str, float] = {"false": 0.0, "true": 0.0}
_pipeline_errors: Dict[str, float] = {stage: float(random.randint(0, 3)) for stage in STAGES}
_retention_deleted = float(random.randint(100, 900))
_db_events = float(random.randint(500, 2000))

# Histogram state: one cumulative bucket count per stage, mirrored on the
# _sum / _count. Bucket order matches BUCKETS + [+Inf]. Initial counts are
# built from one total so +Inf always equals _count.
def _initial_histogram() -> Dict[str, object]:
    total = random.randint(40, 200)
    weights = sorted(random.random() for _ in range(len(BUCKETS) + 1))
    buckets = [float(int(total * weight)) for weight in weights]
    buckets[-1] = float(total)
    return {
        "buckets": buckets,
        "sum": float(total) * random.uniform(0.01, 0.2),
        "count": float(total),
    }


_hist: Dict[str, Dict[str, object]] = {stage: _initial_histogram() for stage in STAGES}

# Retention last success ~2h ago, as required by the fixture contract.
_retention_last_success = time.time() - 7200.0


def _numeric(value: float) -> str:
    """Render a counter/gauge value without exponent noise."""
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.6f}".rstrip("0").rstrip(".")


def _bump(bounds: int, scale: float = 1.0) -> float:
    return random.uniform(0, bounds) * scale


def _advance() -> None:
    """Advance every metric by a small random amount (one scrape)."""
    for key in _events:
        # Low/medium dominate; high/critical stay visible but rarer.
        severity = key[2]
        scale = {"low": 3.0, "medium": 2.0, "high": 1.0, "critical": 0.4}[severity]
        _events[key] += _bump(3.0, scale)

    for svc in _credentials:
        _credentials[svc] += _bump(6.0, 1.0 if svc == "ssh" else 0.4)

    for key in _http:
        _http[key] += _bump(4.0)

    global _ssh_connections, _ssh_handshakes, _ssh_commands, _db_events
    _ssh_connections += _bump(4.0, 0.5)
    _ssh_handshakes += _bump(3.0, 0.5)
    _ssh_commands += _bump(8.0)
    _db_events += _bump(25.0, 0.3)

    # Payloads are rare; only ~20% of scrapes capture metadata.
    for label in _payloads:
        rate = 1.0 if label == "true" else 4.0
        if random.random() < 0.2:
            _payloads[label] += rate

    for stage in _pipeline_errors:
        if random.random() < 0.15:
            _pipeline_errors[stage] += 1.0

    # One to three observations per stage per scrape, cumulative buckets.
    for stage in STAGES:
        state = _hist[stage]
        buckets = state["buckets"]  # type: ignore[assignment]
        for _ in range(random.randint(1, 3)):
            observation = random.choice(
                [0.004, 0.008, 0.02, 0.04, 0.08, 0.2, 0.4, 0.8, 2.0, 4.0, 9.0, 12.0]
            )
            for index, le in enumerate(BUCKETS + [float("inf")]):
                if observation <= le:
                    buckets[index] += 1.0  # type: ignore[index]
            state["sum"] = float(state["sum"]) + observation  # type: ignore[arg-type]
            state["count"] = float(state["count"]) + 1.0  # type: ignore[arg-type]


def _render() -> str:
    """Return the full Prometheus text exposition (format version 0.0.4)."""
    lines: List[str] = []

    def family(name: str, kind: str, help_text: str) -> None:
        lines.append(f"# HELP {name} {help_text}")
        lines.append(f"# TYPE {name} {kind}")

    family("hb_events_total", "counter", "Honeypot events by service, technique and severity.")
    for (svc, tech, sev), value in sorted(_events.items()):
        lines.append(
            f'hb_events_total{{service="{svc}",technique="{tech}",severity="{sev}"}} {_numeric(value)}'
        )

    family("hb_credentials_attempts_total", "counter", "Credential attempts (hash-only capture).")
    for svc, value in sorted(_credentials.items()):
        lines.append(f'hb_credentials_attempts_total{{service="{svc}"}} {_numeric(value)}')

    family("hb_http_requests_total", "counter", "HTTP honeypot requests by method and status.")
    for (method, status), value in sorted(_http.items()):
        lines.append(
            f'hb_http_requests_total{{method="{method}",status="{status}"}} {_numeric(value)}'
        )

    family("hb_ssh_connections_total", "counter", "Accepted SSH TCP connections.")
    lines.append(f"hb_ssh_connections_total {_numeric(_ssh_connections)}")

    # Production can also emit malformed="true"; the fixture keeps only the
    # well-formed stream to stay small.
    family("hb_ssh_handshakes_total", "counter", "SSH handshakes by malformed flag.")
    lines.append(f'hb_ssh_handshakes_total{{malformed="false"}} {_numeric(_ssh_handshakes)}')

    family("hb_ssh_commands_total", "counter", "Commands issued in the fake shell.")
    lines.append(f"hb_ssh_commands_total {_numeric(_ssh_commands)}")

    family("hb_payloads_total", "counter", "Payload metadata captured by quarantine flag.")
    for label, value in sorted(_payloads.items()):
        lines.append(f'hb_payloads_total{{quarantined="{label}"}} {_numeric(value)}')

    family("hb_pipeline_errors_total", "counter", "Enrichment pipeline errors by stage.")
    for stage, value in sorted(_pipeline_errors.items()):
        lines.append(f'hb_pipeline_errors_total{{stage="{stage}"}} {_numeric(value)}')

    family("hb_pipeline_duration_seconds", "histogram", "Enrichment stage duration in seconds.")
    for stage in STAGES:
        state = _hist[stage]
        buckets = state["buckets"]  # type: ignore[assignment]
        for index, le in enumerate(BUCKETS):
            lines.append(
                f'hb_pipeline_duration_seconds_bucket{{stage="{stage}",le="{le}"}} '
                f"{_numeric(buckets[index])}"  # type: ignore[index]
            )
        lines.append(
            f'hb_pipeline_duration_seconds_bucket{{stage="{stage}",le="+Inf"}} '
            f"{_numeric(buckets[-1])}"  # type: ignore[index]
        )
        lines.append(
            f'hb_pipeline_duration_seconds_sum{{stage="{stage}"}} {_numeric(float(state["sum"]))}'
        )
        lines.append(
            f'hb_pipeline_duration_seconds_count{{stage="{stage}"}} {_numeric(float(state["count"]))}'
        )

    family("hb_db_up", "gauge", "1 when PostgreSQL is reachable.")
    lines.append("hb_db_up 1")

    family("hb_db_events", "gauge", "Current number of stored events.")
    lines.append(f"hb_db_events {int(_db_events)}")

    family(
        "hb_retention_last_success_timestamp_seconds",
        "gauge",
        "Unix timestamp of the last successful retention run.",
    )
    lines.append(
        "hb_retention_last_success_timestamp_seconds "
        f"{_numeric(round(_retention_last_success, 3))}"
    )

    family("hb_retention_deleted_total", "counter", "Rows deleted by the retention job.")
    lines.append(f"hb_retention_deleted_total {_numeric(_retention_deleted)}")

    family("hb_build_info", "gauge", "Build information; always 1.")
    lines.append('hb_build_info{version="fixture"} 1')

    # Default exporter metrics are represented by a tiny stand-in so panels
    # using process/python_* families are not empty in the fixture.
    family("process_start_time_seconds", "gauge", "Start time of the process since unix epoch.")
    lines.append(f"process_start_time_seconds {_numeric(round(_boot, 3))}")
    family("process_resident_memory_bytes", "gauge", "Resident memory size in bytes.")
    lines.append(f"process_resident_memory_bytes {_numeric(18 * 1024 * 1024)}")

    return "\n".join(lines) + "\n"


class Handler(BaseHTTPRequestHandler):
    server_version = "HoneyBadgerFixture/1.0"

    def do_GET(self) -> None:  # noqa: N802 - stdlib API
        if self.path.split("?")[0] == "/healthz":
            body = b"ok\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path.split("?")[0] != "/metrics":
            body = b"HoneyBadger metrics fixture (DEV ONLY)\n/metrics\n/healthz\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        with _lock:
            _advance()
            body = _render().encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            return
        print(
            f"[fixture] scrape /metrics from {self.client_address[0]} "
            f"({len(body)} bytes, {body.count(b'# TYPE')} families)",
            flush=True,
        )

    def log_message(self, fmt: str, *args: object) -> None:
        # One intentional line per scrape is logged in do_GET instead.
        return


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"[fixture] HoneyBadger metrics fixture on http://{HOST}:{PORT}/metrics", flush=True)
    print("[fixture] DEV/DEMO ONLY - synthetic data, never production", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[fixture] shutting down", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
