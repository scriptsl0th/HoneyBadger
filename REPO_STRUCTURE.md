# HoneyBadger — Repository Structure

```
HoneyBadger/
│
├── README.md                              # Overview, quick links, key achievements
├── docker-compose.yml                     # Entire stack locally: docker-compose up
├── .env.example                           # Environment variable template
├── .gitignore
│
├── backend/                               # Python honeypot core (one image, one asyncio loop)
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── main.py                            # Entrypoint: wiring, config load, lifecycle
│   ├── config.py                          # pydantic-settings, per-env config
│   ├── schemas.py                         # Pydantic event models + intake contract
│   ├── bus.py                             # Raw + enriched in-process asyncio event buses
│   ├── sshd.py                            # asyncssh honeypot: accept any creds, drop into shell
│   ├── fakeshell.py                       # Fake shell: commands + wget/curl interception
│   ├── httpd.py                           # aiohttp HTTP honeypot (the internet-facing edge)
│   ├── http_routes.py                     # Bait responses (fake login, probe responses)
│   ├── pipeline.py                        # Enrichment pipeline: geoip -> mitre -> credentials
│   ├── geoip.py                           # GeoIpProvider (ip-api default, cached, MaxMind opt-in)
│   ├── mitre.py                           # Rule-based ATT&CK technique classifier
│   ├── credentials.py                     # Credential extraction (hashes only) + top-N counters
│   ├── payloads.py                        # Payload metadata capture (never fetch/execute)
│   ├── api.py                             # REST API (stats) + WebSocket (live events)
│   ├── storage.py                         # Async SQLAlchemy -> PostgreSQL
│   ├── metrics.py                         # Prometheus exporter (:8000)
│   ├── alerts.py                          # Deferred: Prometheus owns alerting
│   ├── retention.py                       # Scheduled purge (> 6 months)
│   ├── db/
│   │   ├── models.py                      # SQLAlchemy models
│   │   └── migrations/                    # Schema migrations
│   ├── sim/
│   │   └── simulate.py                    # Attack simulator / demo + integration driver
│   └── tests/
│       ├── test_fakeshell.py
│       ├── test_mitre.py
│       ├── test_pipeline.py
│       └── test_ssh_handshake.py
│
├── dashboard/                             # React + Vite SPA (TypeScript)
│   ├── package.json
│   ├── package-lock.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── index.html
│   ├── .env.example                        # VITE_API_MODE=api|mock, polling interval
│   ├── Dockerfile                         # Multi-stage build -> nginx static host
│   ├── nginx.conf                         # Proxies /api + /ws -> backend:8090
│   └── src/
│       ├── app.tsx                        # Single-page threat-ops console
│       ├── main.tsx
│       ├── types.ts                       # EventOut / stats / WS types
│       ├── api/                           # client.ts, endpoints.ts, mock.ts
│       ├── ws/                            # client.ts (reconnect + backoff)
│       ├── hooks/                         # useLiveEvents, useStats, useTimeseries, ...
│       ├── components/
│       │   ├── layout/                    # TopBar, KpiRow, Panel
│       │   ├── charts/                    # ActivityChart, TechniqueBars, ServiceDonut
│       │   ├── map/                       # GeoMap (world attack map)
│       │   ├── feed/                      # EventTable, EventRow, EventDetailDrawer
│       │   ├── panels/                    # TopCredentials, TopSources, Payloads
│       │   └── ui/                        # Badge, SeverityDot, ErrorState, ...
│       ├── lib/                           # format, severity, techniques, colors (+ tests)
│       └── styles.css                     # global console styles
│
├── monitoring/
│   ├── README.md                          # Ops stack + fixtures preview
│   ├── prometheus/
│   │   ├── prometheus.yml                 # Scrape configs (backend:8000)
│   │   └── rules/
│   │       ├── alerts.yml                 # Single source of alert thresholds
│   │       └── recording-rules.yml
│   ├── alertmanager/
│   │   └── alertmanager.yml               # Routes alerts from Prometheus
│   ├── grafana/
│   │   ├── README.md
│   │   ├── provisioning/
│   │   │   ├── datasources/prometheus.yml # Prometheus datasource
│   │   │   ├── dashboards/dashboards.yml  # Dashboard provider config
│   │   │   └── alerting/                  # Reserved (Grafana owns no alert rules)
│   │   └── dashboards/                    # overview.json, attack-patterns.json, pipeline-health.json
│   └── fixtures/
│       ├── metrics_fixture.py             # Dev-only synthetic metrics (:9101)
│       └── README.md
│
├── docs/
│   ├── ARCHITECTURE.md                    # Component map, data ownership, safety
│   ├── API.md                             # Agreed REST + WebSocket + metrics contract
│   ├── ANALYSIS.md                        # Sample findings + interpretation template (empty)
│   ├── RESPONSIBLE_DISCLOSURE.md          # Ethics + responsible handling (empty)
│   └── ROADMAP.md                         # Incremental slice plan + current status
│
├── tests/
│   ├── integration/
│   │   ├── test_end_to_end.sh             # Full flow
│   │   └── test_api_contract.py           # Intake API compatibility
│   ├── security/
│   │   ├── test_network_isolation.sh      # Verify containment
│   │   └── test_credentials.sh            # Verify hash-only policy
│   └── fixtures/                          # Sample events, mock geoip data
```

---

## Quick reference

### Ports
| Service | Container | Host |
|---|---|---|
| SSH honeypot | 8022 | 8022 |
| HTTP honeypot (httpd) | 8081 | 8081 |
| Metrics | 8000 | 8000 |
| Intake API + WebSocket | 8090 | 8090 |
| Dashboard | 80 or 5173 (dev) | 3000 |
| PostgreSQL | 5432 | `127.0.0.1:5432` (loopback only) |
| Prometheus | 9090 | 9090 |
| Alertmanager | 9093 | 9093 |
| Grafana | 3000 | 3001 | (container→host)
| Fixtures exporter (dev profile) | 9101 | `127.0.0.1:9101` |

### Event flow
```
sshd.py / httpd.py
      |  publish
      v
 raw bus ──▶ pipeline.py ──▶ geoip.py ──▶ mitre.py ──▶ credentials.py
               |                                     |
               |           enriched bus ◀────────────┘
               |                     |
               v                     v
         storage.py             api.py (REST :8090 + WS) ──▶ dashboard/
         (PostgreSQL)           metrics.py (:8000) ──▶ Prometheus (:9090)
                                                        ├──▶ Grafana (:3001)
                                                        └──▶ Alertmanager (:9093)
```

### Key design properties (non-negotiable)
- **Credentials**: SHA-256 hashes only — plaintext passwords never touch disk. Top-N counters kept in memory/memory-backed tables for the dashboard.
- **Payloads**: metadata-only by default (URL, hash, size). `CAPTURE_PAYLOADS` opt-in drops files to a **noexec quarantine dir** — nothing is ever fetched to or executed on the host.
- **Containment**: captured artifacts never reach host filesystem or network; PostgreSQL is loopback-only. The compose bridge allows GeoIP egress (`ip-api`); tightening it is a backend-slice decision.
- **Alerts**: Prometheus evaluates rules in `monitoring/prometheus/rules/alerts.yml` and is the single alerting authority. Alertmanager routes those alerts; `backend/alerts.py` is deferred and the backend never pushes alerts. No "login success" alert (the honeypot always accepts credentials).
- **Retention**: single value — 6 months — enforced by `retention.py`; Prometheus keeps 15 days of metrics.
- **MITRE**: events auto-classified (T1110, T1595, T1190, T1105, T1059, T1078); asserted by the simulator in tests.

---

## Getting started

```bash
# Clone
git clone https://github.com/scriptsl0th/HoneyBadger.git
cd honeybadger

# Copy the env template, then start the stack
cp .env.example .env
docker compose up -d

# Preview Grafana with synthetic metrics before the backend exists
docker compose --profile fixtures up -d

# Access services (see port table)
# Dashboard:   http://localhost:3000
# Intake API:  http://localhost:8090
# Prometheus:  http://localhost:9090
# Grafana:     http://localhost:3001
# Alertmanager http://localhost:9093
```

`docker-compose.yml` is complete; `backend/Dockerfile` builds the SSH honeypot
and intake API/WebSocket image. Monitoring services start independently, and
dashboard nginx serves the SPA even when the backend is absent.