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
│   ├── alerts.py                          # Threshold checks -> Alertmanager
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
│   ├── vite.config.ts
│   ├── Dockerfile                         # Multi-stage build -> static host
│   └── src/
│       ├── app.tsx                        # Main dashboard
│       ├── api/                           # REST polling client
│       ├── ws/                            # WebSocket live-event client
│       ├── components/                    # Charts, table, geo map, cards
│       └── hooks/                         # useLiveEvents, useStats, etc.
│
├── monitoring/
│   ├── prometheus/
│   │   ├── prometheus.yml                 # Scrape configs
│   │   ├── rules/
│   │   │   ├── alerts.yml                 # Fixed alert rules (rate, payload, health)
│   │   │   └── recording-rules.yml
│   │   └── Dockerfile
│   ├── grafana/
│   │   ├── provisioning/
│   │   │   ├── datasources/               # Prometheus datasource
│   │   │   └── dashboards/                # Provisioned dashboards
│   │   └── Dockerfile
│   └── alertmanager/
│       ├── alertmanager.yml
│       └── Dockerfile
│
├── docs/
│   ├── ARCHITECTURE.md                    # System design + diagrams (matches code)
│   ├── ANALYSIS.md                        # Sample findings + interpretation template
│   ├── RESPONSIBLE_DISCLOSURE.md          # Ethics + responsible handling
│   └── API.md                             # REST + WebSocket API documentation
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
| SSH honeypot | 22 | 8022 |
| HTTP honeypot (httpd) | 8081 | 8081 |
| Metrics | 8000 | 8000 |
| Intake API | 8090 | 8090 |
| Dashboard | 80 or 5173 (dev) | 3000 |
| PostgreSQL | 5432 | 5432 |
| Prometheus | 9090 | 9090 |
| Alertmanager | 9093 | 9093 |
| Grafana | 3000 | 3000 |

### Event flow
```
sshd.py / httpd.py
      |  publish
      v
 raw bus ──▶ pipeline.py ──▶ geoip.py ──▶ mitre.py ──▶ credentials.py
               |                                     |
               |            enriched bus ◀───────────┘
               |                      |
               v                      v
         storage.py              api.py (REST + WS) ──▶ dashboard/
         (PostgreSQL)            metrics.py ──▶ Prometheus ──▶ Grafana + Alertmanager
```

### Key design properties (non-negotiable)
- **Credentials**: SHA-256 hashes only — plaintext passwords never touch disk. Top-N counters kept in memory/memory-backed tables for the dashboard.
- **Payloads**: metadata-only by default (URL, hash, size). `CAPTURE_PAYLOADS` opt-in drops files to a **noexec quarantine dir** — nothing is ever fetched to or executed on the host.
- **Containment**: the honeypot network is isolated; captured artifacts never reach host filesystem or network.
- **Alerts**: based on brute-force rate, payload capture, retention lag, service health. No "login success" alert (the honeypot always accepts credentials).
- **Retention**: single value — 6 months — enforced by `retention.py`.
- **MITRE**: events auto-classified (T1110, T1595, T1190, T1105, T1059, T1078); asserted by the simulator in tests.

---

## Getting started (planned)

```bash
# Clone
git clone https://github.com/yourusername/honeybadger.git
cd honeybadger

# Local development
docker-compose up -d
docker-compose logs -f

# Access services (see port table)
# Dashboard:   http://localhost:3000
# Intake API:  http://localhost:8090
# Prometheus:  http://localhost:9090
# Grafana:     http://localhost:3000/grafana
```