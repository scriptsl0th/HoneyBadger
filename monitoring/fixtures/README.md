# HoneyBadger metrics fixture (DEV/DEMO ONLY)

`metrics_fixture.py` is a zero-dependency (Python 3 stdlib) synthetic
Prometheus exporter on **:9101/metrics**. It exists so every Grafana panel,
recording rule and alert threshold can be validated before
`backend/metrics.py` is implemented.

It is **never part of production** and is only started under the `fixtures`
compose profile.

## What it emits

The full metric contract from `../README.md`: `hb_events_total` (7 techniques x
4 severities x 2 services), `hb_credentials_attempts_total`,
`hb_http_requests_total`, `hb_ssh_*`, `hb_payloads_total`,
`hb_pipeline_errors_total`, a cumulative `hb_pipeline_duration_seconds`
histogram, and the `hb_db_*` / `hb_retention_*` / `hb_build_info` gauges.
Counters advance a little on every scrape, so `rate()`/`increase()` panels move.

## Run with compose (preferred)

```bash
docker compose --profile fixtures up -d fixtures prometheus grafana
```

Prometheus then scrapes `fixtures:9101` via the `honeybadger-fixtures` job.
Without the profile that job is **DOWN**, which is expected and does not fire
`HoneyBadgerDown` (that alert only watches `honeybadger-backend`).

## Run standalone with Docker

```bash
docker run --rm -p 9101:9101 \
  -v "${PWD}/monitoring/fixtures:/app:ro" \
  python:3.12-alpine python /app/metrics_fixture.py
```

## Run locally

```bash
python monitoring/fixtures/metrics_fixture.py
curl http://localhost:9101/metrics
curl http://localhost:9101/healthz
```

Useful checks:

```bash
curl -s http://localhost:9101/metrics | Select-String '^# TYPE'
curl -s http://localhost:9101/metrics | Select-String 'hb_pipeline_duration_seconds_bucket'
```

Stop it with `Ctrl+C`; there is no state on disk. `FIXTURE_PORT` overrides
9101 and `FIXTURE_HOST` overrides `0.0.0.0`.
