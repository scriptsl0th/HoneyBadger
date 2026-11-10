"""Prometheus metrics exporter for HoneyBadger.

Exposes metrics on port 8000 for Prometheus scraping.
Metric names follow the hb_* prefix convention.
"""

import logging
from typing import Optional

from prometheus_client import Counter, Gauge, Histogram, start_http_server

logger = logging.getLogger(__name__)

# Event metrics
hb_events_total = Counter(
    "hb_events_total",
    "Total events captured",
    ["service", "technique", "severity"],
)

hb_events_by_service = Counter(
    "hb_events_by_service_total",
    "Total events by service",
    ["service"],
)

hb_events_by_severity = Counter(
    "hb_events_by_severity_total",
    "Total events by severity",
    ["severity"],
)

hb_events_by_technique = Counter(
    "hb_events_by_technique_total",
    "Total events by MITRE ATT&CK technique",
    ["technique"],
)

# Authentication metrics
hb_credentials_attempts_total = Counter(
    "hb_credentials_attempts_total",
    "Total credential attempts (SSH + HTTP)",
    ["service", "username"],
)

hb_unique_credentials = Gauge(
    "hb_unique_credentials",
    "Number of unique credential pairs seen",
)

hb_top_credential_count = Gauge(
    "hb_top_credential_count",
    "Count of the most attempted credential pair",
)

# Payload metrics
hb_payloads_captured_total = Counter(
    "hb_payloads_captured_total",
    "Total payload metadata captured",
)

hb_payloads_quarantined_total = Counter(
    "hb_payloads_quarantined_total",
    "Total payloads quarantined",
)

hb_payload_size_bytes = Histogram(
    "hb_payload_size_bytes",
    "Size of captured payloads in bytes",
    buckets=[100, 1000, 10000, 100000, 1000000, 10000000],
)

# Pipeline health metrics
hb_pipeline_latency_seconds = Histogram(
    "hb_pipeline_latency_seconds",
    "Pipeline processing latency in seconds",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

hb_pipeline_errors_total = Counter(
    "hb_pipeline_errors_total",
    "Total pipeline errors by stage",
    ["stage"],
)

# GeoIP metrics
hb_geoip_lookups_total = Counter(
    "hb_geoip_lookups_total",
    "Total GeoIP lookups",
    ["provider", "result"],  # result: hit, miss, error
)

hb_geoip_cache_hits = Counter(
    "hb_geoip_cache_hits_total",
    "GeoIP cache hits",
)

hb_geoip_cache_misses = Counter(
    "hb_geoip_cache_misses_total",
    "GeoIP cache misses",
)

hb_geoip_cache_size = Gauge(
    "hb_geoip_cache_size",
    "Number of entries in GeoIP cache",
)

# Storage metrics
hb_storage_write_latency_seconds = Histogram(
    "hb_storage_write_latency_seconds",
    "Database write latency in seconds",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

hb_storage_errors_total = Counter(
    "hb_storage_errors_total",
    "Total database errors",
    ["operation"],
)

hb_db_events = Gauge(
    "hb_db_events",
    "Total events in database",
)

hb_db_up = Gauge(
    "hb_db_up",
    "Database connectivity (1=up, 0=down)",
)

# HTTP honeypot metrics
hb_http_requests_total = Counter(
    "hb_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

hb_http_bait_hits_total = Counter(
    "hb_http_bait_hits_total",
    "HTTP bait route hits",
    ["route"],
)

hb_http_request_latency_seconds = Histogram(
    "hb_http_request_latency_seconds",
    "HTTP request latency in seconds",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

# SSH honeypot metrics
hb_ssh_connections_total = Counter(
    "hb_ssh_connections_total",
    "Total SSH connections",
)

hb_ssh_handshakes_total = Counter(
    "hb_ssh_handshakes_total",
    "Total SSH handshakes",
    ["malformed"],
)

hb_ssh_auth_attempts_total = Counter(
    "hb_ssh_auth_attempts_total",
    "Total SSH auth attempts",
    ["username"],
)

hb_ssh_commands_total = Counter(
    "hb_ssh_commands_total",
    "Total SSH commands executed",
    ["command"],
)

# Retention metrics
hb_retention_runs_total = Counter(
    "hb_retention_runs_total",
    "Total retention job runs",
    ["result"],  # success, error
)

hb_retention_deleted_rows = Counter(
    "hb_retention_deleted_rows",
    "Total rows deleted by retention job",
    ["table"],
)

hb_retention_last_success_timestamp_seconds = Gauge(
    "hb_retention_last_success_timestamp_seconds",
    "Unix timestamp of last successful retention run",
)

# API metrics
hb_api_requests_total = Counter(
    "hb_api_requests_total",
    "Total API requests",
    ["endpoint", "method", "status"],
)

hb_api_request_latency_seconds = Histogram(
    "hb_api_request_latency_seconds",
    "API request latency in seconds",
    ["endpoint"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

hb_ws_connections_active = Gauge(
    "hb_ws_connections_active",
    "Active WebSocket connections",
)

# System metrics
hb_uptime_seconds = Gauge(
    "hb_uptime_seconds",
    "Process uptime in seconds",
)

hb_info = Gauge(
    "hb_info",
    "HoneyBadger version and build info",
    ["version", "build_date"],
)


def start_metrics_server(port: int = 8000) -> None:
    """Start the Prometheus metrics HTTP server."""
    start_http_server(port)
    logger.info("Prometheus metrics server started on port %d", port)


# Helper functions for emitting metrics from components

def record_event(service: str, technique: Optional[str], severity: Optional[str]) -> None:
    """Record an event metric."""
    hb_events_total.labels(
        service=service,
        technique=technique or "unknown",
        severity=severity or "unknown",
    ).inc()
    hb_events_by_service.labels(service=service).inc()
    if severity:
        hb_events_by_severity.labels(severity=severity).inc()
    if technique:
        hb_events_by_technique.labels(technique=technique).inc()


def record_credential_attempt(service: str, username: str) -> None:
    """Record a credential attempt."""
    hb_credentials_attempts_total.labels(service=service, username=username).inc()


def record_unique_credentials(count: int) -> None:
    """Update unique credentials gauge."""
    hb_unique_credentials.set(count)


def record_top_credential_count(count: int) -> None:
    """Update top credential count gauge."""
    hb_top_credential_count.set(count)


def record_payload_captured(size: Optional[int] = None) -> None:
    """Record a captured payload."""
    hb_payloads_captured_total.inc()
    if size is not None:
        hb_payload_size_bytes.observe(size)


def record_payload_quarantined() -> None:
    """Record a quarantined payload."""
    hb_payloads_quarantined_total.inc()


def record_pipeline_latency(latency: float) -> None:
    """Record pipeline processing latency."""
    hb_pipeline_latency_seconds.observe(latency)


def record_pipeline_error(stage: str) -> None:
    """Record a pipeline error."""
    hb_pipeline_errors_total.labels(stage=stage).inc()


def record_geoip_lookup(provider: str, result: str) -> None:
    """Record a GeoIP lookup."""
    hb_geoip_lookups_total.labels(provider=provider, result=result).inc()


def record_geoip_cache_hit() -> None:
    """Record a GeoIP cache hit."""
    hb_geoip_cache_hits.inc()


def record_geoip_cache_miss() -> None:
    """Record a GeoIP cache miss."""
    hb_geoip_cache_misses.inc()


def record_geoip_cache_size(size: int) -> None:
    """Update GeoIP cache size gauge."""
    hb_geoip_cache_size.set(size)


def record_storage_write(operation: str, latency: float) -> None:
    """Record a storage write."""
    hb_storage_write_latency_seconds.labels(operation=operation).observe(latency)


def record_storage_error(operation: str) -> None:
    """Record a storage error."""
    hb_storage_errors_total.labels(operation=operation).inc()


def record_db_events(count: int) -> None:
    """Update total events in database gauge."""
    hb_db_events.set(count)


def record_db_up(up: bool) -> None:
    """Update database connectivity gauge."""
    hb_db_up.set(1 if up else 0)


def record_http_request(method: str, path: str, status: int) -> None:
    """Record an HTTP request."""
    hb_http_requests_total.labels(method=method, path=path, status=str(status)).inc()


def record_http_bait_hit(route: str) -> None:
    """Record a bait route hit."""
    hb_http_bait_hits_total.labels(route=route).inc()


def record_http_latency(latency: float) -> None:
    """Record HTTP request latency."""
    hb_http_request_latency_seconds.observe(latency)


def record_ssh_connection() -> None:
    """Record an SSH connection."""
    hb_ssh_connections_total.inc()


def record_ssh_handshake(malformed: bool) -> None:
    """Record an SSH handshake."""
    hb_ssh_handshakes_total.labels(malformed=str(malformed).lower()).inc()


def record_ssh_auth(username: str) -> None:
    """Record an SSH auth attempt."""
    hb_ssh_auth_attempts_total.labels(username=username).inc()


def record_ssh_command(command: str) -> None:
    """Record an SSH command."""
    # Extract base command name
    base_cmd = command.strip().split()[0] if command.strip() else "unknown"
    hb_ssh_commands_total.labels(command=base_cmd).inc()


def record_retention_run(result: str) -> None:
    """Record a retention job run."""
    hb_retention_runs_total.labels(result=result).inc()


def record_retention_deleted(table: str, count: int) -> None:
    """Record rows deleted by retention."""
    hb_retention_deleted_rows.labels(table=table).inc(count)


def record_retention_last_success(timestamp: float) -> None:
    """Record last successful retention run timestamp."""
    hb_retention_last_success_timestamp_seconds.set(timestamp)


def record_api_request(endpoint: str, method: str, status: int) -> None:
    """Record an API request."""
    hb_api_requests_total.labels(endpoint=endpoint, method=method, status=str(status)).inc()


def record_api_latency(endpoint: str, latency: float) -> None:
    """Record API request latency."""
    hb_api_request_latency_seconds.labels(endpoint=endpoint).observe(latency)


def record_ws_connections(count: int) -> None:
    """Record active WebSocket connections."""
    hb_ws_connections_active.set(count)


def record_uptime(seconds: float) -> None:
    """Record process uptime."""
    hb_uptime_seconds.set(seconds)


def set_info(version: str, build_date: str) -> None:
    """Set build info."""
    hb_info.labels(version=version, build_date=build_date).set(1)