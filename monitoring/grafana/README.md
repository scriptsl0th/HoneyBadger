# Grafana — HoneyBadger

Grafana is the **aggregate, read-only** view of the honeypot: traffic volume, attack
techniques, edge protocols, pipeline health and runtime status. It is provisioned
entirely from files in this directory — no clicking required, and no dashboards are
stored only in the database.

- URL: <http://localhost:3001> (host port **3001** → container port 3000)
- Admin credentials: set in `.env` (wired into the container by `docker-compose.yml`
  as `GF_SECURITY_ADMIN_USER` / `GF_SECURITY_ADMIN_PASSWORD`)
- Anonymous access: enabled as **Viewer** for the demo, so the dashboards open without
  a login. Viewers cannot save or edit; only admins can edit in the UI, and the
  provisioned dashboards are read-only (`allowUiUpdates: false`, `editable: false`).
- Folder: **HoneyBadger**
- Datasource: **Prometheus**, fixed UID `prometheus`, default datasource, not editable,
  pointing at `http://prometheus:9090` on the compose network.

The backend metrics exporter does not have to be finished for the dashboards to be
usable: every panel is written to render a `no data yet` placeholder when its series is
absent, rather than an error.

## Layout

```
monitoring/grafana/
├── provisioning/
│   ├── datasources/prometheus.yml   # Prometheus datasource, uid: prometheus
│   ├── dashboards/dashboards.yml    # file provider -> folder "HoneyBadger"
│   ├── plugins/.gitkeep             # keeps Grafana quiet at startup
│   └── alerting/.gitkeep            # keeps Grafana quiet at startup
└── dashboards/
    ├── overview.json                # uid hb-overview
    ├── attack-patterns.json         # uid hb-attack-patterns
    └── pipeline-health.json         # uid hb-pipeline-health
```

The official `grafana/grafana` image is used; there is no custom Dockerfile in this
directory.

## Dashboards

| Dashboard | UID | What it answers |
| --- | --- | --- |
| HoneyBadger — Overview | `hb-overview` | Is it alive, how much traffic, which services/severities/techniques, edge protocols, pipeline errors and enrichment latency. |
| HoneyBadger — Attack Patterns | `hb-attack-patterns` | Which techniques are trending, current per-technique rates, auth attempts vs. their 1h baseline, payload captures, HTTP status mix. |
| HoneyBadger — Pipeline Health | `hb-pipeline-health` | Scrape/DB availability, errors by stage, enrichment P95, process CPU/RSS/FDs, restarts, retention lag and deletions, firing alerts. |

All three share:

- `schemaVersion: 39`, `refresh: 30s`, default range `now-6h`, browser timezone;
- tags `honeybadger`, `honeypot`, `security`;
- a Prometheus annotation query for `ALERTS{alertstate="firing"}` (red markers);
- templating variables `$service`, `$technique`, `$severity`, all multi-select with an
  `All` option (`allValue: ".*"`) and `refresh: 2`, sourced from `hb_events_total`.

Query conventions: `$__rate_interval` / `$__interval` in `rate()` and `increase()`,
`topk(7, …)` for per-label breakdowns, and **no high-cardinality labels**
(`source_ip`, `username`, `country`, paths, credentials). If you add a panel, keep it
that way — aggregate labels only.

## Adding a dashboard

1. Create `monitoring/grafana/dashboards/<name>.json` with a unique top-level `uid`
   (for example `hb-my-view`), `schemaVersion: 39`, the standard tags, and panel
   datasources of `{"type": "prometheus", "uid": "prometheus"}`.
2. Keep panels on the 24-column grid: every `gridPos` must satisfy `x + w <= 24` and
   must not overlap another panel. Use `row` panels to group sections.
3. Give every panel a unique integer `id`, a title, a `fieldConfig.defaults.unit`, and
   `options.noValue: "no data yet"`.
4. Provisioning picks the file up automatically within 30 seconds
   (`updateIntervalSeconds: 30`). No restart needed. To pick it up immediately:

   ```powershell
   docker compose restart grafana
   ```

The provider sets `disableDeletion: false`, so deleting a JSON file removes the
dashboard on the next provisioning pass. Edits made in the UI are overwritten by the
file (`allowUiUpdates: false`) — change the JSON, not the browser.

## Re-provisioning / troubleshooting

```powershell
# recreate just Grafana with the current files
docker compose up -d --force-recreate grafana

# watch provisioning decisions and any file errors
docker logs -f honeybadger-grafana   # service name may differ; check docker compose ps

# confirm the datasource and dashboards came up
curl http://localhost:3001/api/health
curl "http://localhost:3001/api/search?query=HoneyBadger"
```

Common causes of an empty dashboard:

- **Datasource UID mismatch** — every panel and target must reference
  `{"type": "prometheus", "uid": "prometheus"}`, not a name or a generated UID.
- **Prometheus unreachable** from the Grafana container — check that both are on the
  same compose network and the URL is `http://prometheus:9090`.
- **Series not exported yet** — expected during rollout; panels show `no data yet`.
  Recording rules such as `hb:events:rate5m` only appear after Prometheus has evaluated
  them, and `hb_*` counters only appear after the backend serves `/metrics`.

## What is deliberately *not* in Grafana

- **Geographic map view** — GeoIP enrichment lives in PostgreSQL; country/city are not
  Prometheus labels (unbounded cardinality).
- **Per-IP, per-path and per-credential detail** — stored in Postgres and rendered by
  the React dashboard at <http://localhost:3000>. Prometheus keeps only aggregate
  dimensions so that an attack cannot blow up the time series database.

Use Grafana for trends and service health, the React dashboard for investigation.
