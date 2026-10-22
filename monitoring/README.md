# HoneyBadger monitoring (Prometheus + Alertmanager)

Prometheus scrapes the honeypot backend's exporter, evaluates recording and
alerting rules, and hands firing alerts to Alertmanager. Grafana
(`:3001`) reads Prometheus; the React dashboard (`:3000`) reads the
Postgres-backed REST API and never touches Prometheus.

```
backend /metrics  --pull-->  Prometheus  --rules-->  Alertmanager  -->  :9093 UI
                                  |
                                  +-->  Grafana :3001 (dashboards)
```

There is no push path and no alert delivery by default: everything is visible
locally at `http://localhost:9093` and **nothing leaves the host**.

## Ports and URLs

| Service | Port | URL |
|---|---|---|
| Prometheus | 9090 | http://localhost:9090 (`/-/targets`, `/-/rules`, `/graph`) |
| Alertmanager | 9093 | http://localhost:9093 |
| Grafana | 3001 | http://localhost:3001 |
| React dashboard | 3000 | http://localhost:3000 (Postgres-backed REST, not Prometheus) |
| Backend exporter | 8000 | http://localhost:8000/metrics |
| Fixture exporter (dev) | 9101 | http://localhost:9101/metrics |

## Files

| Path | Purpose |
|---|---|
| `prometheus/prometheus.yml` | Scrape configs (`prometheus`, `honeybadger-backend`, `honeybadger-fixtures`), rule glob, Alertmanager target |
| `prometheus/rules/recording-rules.yml` | Precomputed rates/ratios used by dashboards and alerts |
| `prometheus/rules/alerts.yml` | The 7 fixed alert rules and their thresholds |
| `alertmanager/alertmanager.yml` | Grouping, inhibition, UI-only receivers, commented webhook/email examples |
| `fixtures/metrics_fixture.py` | Stdlib synthetic exporter for dashboards before the backend exporter exists |
| `fixtures/README.md` | How to run the fixture |
| `grafana/` | Grafana provisioning (owned separately: datasource + dashboards) |

Official images are used (`prom/prometheus`, `prom/alertmanager`); there are no
Dockerfiles in this directory.

## Alert flow

1. The backend exposes `http://backend:8000/metrics` with the metric contract
   below. Prometheus pulls it every 15s (`honeybadger-backend` job).
2. Prometheus records `hb:*` series every 30s and evaluates
   `honeybadger.alerts` every 30s (Prometheus's own evaluation interval is 15s,
   the group interval 30s).
3. A rule that stays true for its `for:` duration is sent to
   `alertmanager:9093` (`alerting.alertmanagers` in `prometheus.yml`).
4. Alertmanager groups by `alertname, severity`, waits 10s, and shows the alert
   in its UI. Critical alerts repeat hourly; everything else every 4h.
   `HoneyBadgerDown` inhibits derived `warning|info` alerts for the same job.

The backend does **not** push alerts or metrics. Alert thresholds live only in
`prometheus/rules/alerts.yml`; `backend/alerts.py` is deliberately not used, so
there is exactly one alerting authority.

## Metric contract

The backend must expose exactly these names/labels at `/metrics`. Label values
in comments are the allowed set.

| Metric | Type | Labels | Meaning |
|---|---|---|---|
| `hb_events_total` | counter | `service`, `technique`, `severity` | Enriched events (`ssh`/`http`, ATT&CK id, `low`/`medium`/`high`/`critical`) |
| `hb_credentials_attempts_total` | counter | `service` | Credential attempts (hash-only; never plaintext) |
| `hb_http_requests_total` | counter | `method`, `status` | HTTP honeypot responses |
| `hb_ssh_connections_total` | counter | — | Accepted SSH connections |
| `hb_ssh_handshakes_total` | counter | `malformed` | SSH handshakes, split by malformed flag |
| `hb_ssh_commands_total` | counter | — | Commands executed in the fake shell |
| `hb_payloads_total` | counter | `quarantined` | Payload metadata captured, by quarantine state |
| `hb_pipeline_errors_total` | counter | `stage` | Errors per enrichment stage (`geoip`, `mitre`, `credentials`, `storage`) |
| `hb_pipeline_duration_seconds` | histogram | `stage` | Stage latency; exposes `_bucket`, `_sum`, `_count` |
| `hb_db_up` | gauge | — | `1` when Postgres is reachable, else `0` |
| `hb_db_events` | gauge | — | Rows currently stored |
| `hb_retention_last_success_timestamp_seconds` | gauge | — | Unix epoch seconds of last successful retention run |
| `hb_retention_deleted_total` | counter | — | Rows deleted by retention |
| `hb_build_info` | gauge | `version` | Always `1`; carries the build version |

The default exporter families (`python_*`, `process_*`) are expected too and are
what the "process" row of the Grafana dashboards uses.

### Cardinality policy (non-negotiable)

Never add labels for `source_ip`, `username`, `password_hash`, `http_path`, or
`country` (or anything else attacker-controlled and unbounded). Those belong in
Postgres, which the React dashboard queries. Prometheus labels stay in a small,
fixed set: `service`, `technique`, `severity`, `stage`, `method`, `status`,
`malformed`, `quarantined`, plus `job`/`instance`/`env` added by scrape configs.
This keeps the series count bounded even during a spoofed-source flood, and
avoids leaking personal data into a time-series database with 15-day retention.

## Retention

- **Prometheus: 15 days** (set by the compose `--storage.tsdb.retention.time=15d`
  flag). Long enough for rate/ratio alerting and Grafana trend panels.
- **PostgreSQL: 180 days** (`RETENTION_DAYS`, enforced by `retention.py`, alarms
  if the job lags 36h). The dashboard and all investigation work use Postgres.

Prometheus is a monitoring cache, not the system of record. Do not raise its
retention to match Postgres.

## Tuning thresholds

Every threshold lives in `prometheus/rules/alerts.yml`; recording rules live in
`recording-rules.yml`. Edit the file, validate it (commands below), then reload
without restarting Prometheus (the compose command enables
`--web.enable-lifecycle`):

```bash
curl -X POST http://localhost:9090/-/reload
```

Check the result at http://localhost:9090/-/rules and
http://localhost:9090/-/alerts. Rule groups evaluate every 30s; `for:` times are
counted from when the expression first becomes true.

Common adjustments:

- Internet-facing SSH noise: raise `BruteForceWave`'s `0.5` (30 attempts/min).
- More/less sensitive attack surge: change `CriticalAttackSurge`'s `0.17`
  (~10 high/critical events/min).
- Payload review: `PayloadCaptured` fires on any increase in 10 minutes; add a
  minimum count (e.g. `> 5`) if capture is noisy.
- Slow pipeline: add a `histogram_quantile(0.95, ...)` rule on
  `hb_pipeline_duration_seconds_bucket` before alerting.

## Fixture usage

`fixtures/metrics_fixture.py` emits synthetic data for every metric above so
dashboards can be validated before `backend/metrics.py` exists.

```bash
docker compose --profile fixtures up -d fixtures
# or standalone:
docker run --rm -p 9101:9101 -v "${PWD}/monitoring/fixtures:/app:ro" \
  python:3.12-alpine python /app/metrics_fixture.py
```

The `honeybadger-fixtures` job is DOWN when the profile is off - that is
expected and does not alert. See `fixtures/README.md` for details.

## Validation

Run from the repository root (PowerShell / bash):

```bash
docker run --rm -v "${PWD}/monitoring/prometheus:/etc/prometheus:ro" --entrypoint promtool prom/prometheus:latest check config /etc/prometheus/prometheus.yml
docker run --rm -v "${PWD}/monitoring/prometheus:/etc/prometheus:ro" --entrypoint promtool prom/prometheus:latest check rules /etc/prometheus/rules/recording-rules.yml /etc/prometheus/rules/alerts.yml
docker run --rm -v "${PWD}/monitoring/alertmanager:/etc/alertmanager:ro" --entrypoint amtool prom/alertmanager:latest check-config /etc/alertmanager/alertmanager.yml
```

Expected: `SUCCESS` from both promtool commands and `SUCCESS` from amtool.

`docker-compose.yml` pins `prom/prometheus:v3.15.1` and
`prom/alertmanager:v0.34.1`; the commands above use `:latest`. Replace the tag
with the pinned version to validate exactly what compose runs.

Optional, to confirm the exporter contract in the browser:

```bash
curl -s http://localhost:8000/metrics | Select-String 'hb_events_total|hb_build_info'
```

## Alerts

All alerts carry `team: honeybadger`, `service: honeypot`, a `severity`, and one
`category` (`availability` / `security` / `pipeline`).

| Alert | Condition | For | Severity | Category |
|---|---|---|---|---|
| `HoneyBadgerDown` | `up{job="honeybadger-backend"} == 0` | 2m | critical | availability |
| `DatabaseUnreachable` | `hb_db_up == 0` | 2m | critical | availability |
| `BruteForceWave` | `sum(rate(hb_credentials_attempts_total[5m])) > 0.5` (>30/min) | 5m | warning | security |
| `CriticalAttackSurge` | `sum(rate(hb_events_total{severity=~"high\|critical"}[5m])) > 0.17` (~10/min) | 10m | warning | security |
| `PayloadCaptured` | `sum(increase(hb_payloads_total[10m])) > 0` | 0m | warning | security |
| `PipelineErrors` | `sum(rate(hb_pipeline_errors_total[5m])) > 0.05` | 10m | warning | pipeline |
| `RetentionLag` | `time() - hb_retention_last_success_timestamp_seconds > 129600` (36h) | 10m | warning | pipeline |

There is intentionally **no "login success" alert** (the honeypots accept every
credential by design) and **no "no events" alert** (an idle honeypot is normal;
internet background noise can drop to zero).

## Troubleshooting

- `honeybadger-fixtures` target DOWN: start the `fixtures` profile, otherwise
  ignore it.
- No `hb_*` series: confirm `curl http://localhost:8000/metrics` works from the
  backend container and check http://localhost:9090/targets.
- Alerts firing but not visible: query http://localhost:9090/api/v1/alerts,
  then confirm `alertmanager:9093` is reachable on the compose network.
- Rule edit ignored: you forgot `POST /-/reload` (or the config failed to load;
  check the Prometheus logs).
