# HoneyBadger — Architecture

Design-level companion to `README.md` / `SYSTEM_ARCHITECTURE.md`;
`docs/API.md` is the wire-level contract.

## 1. Component map and event pipeline

```
 attacker
    │ SSH :8022              HTTP :8081
    ▼                         ▼
┌────────────────────────────────────────────────┐
│ backend (one container, one asyncio loop)      │
│ sshd ─► fakeshell ─┐                           │
│ httpd ─► routes ───┤ raw bus                   │
│                    ▼                           │
│              pipeline.py                       │
│   geoip │ mitre │ credentials │ payloads       │
│                    │                           │
│              enriched bus                      │
│          ┌─────────┴─────────┐                 │
│          ▼                   ▼                 │
│     storage.py         api.py / metrics.py     │
└──────────┬───────────────────┬─────────────────┘
           │                   │
   ┌───────▼──────┐    ┌───────▼──────────────┐
   │ PostgreSQL   │    │ api :8090 (REST + WS)│
   │ events / agg │    │ metrics :8000        │
   └──────────────┘    └───────┬──────────────┘
                               │ /api, /ws
                    ┌──────────▼──────────┐
                    │ dashboard :3000     │
                    │ React threat console│
                    └─────────────────────┘

 metrics :8000 ─► Prometheus :9090 ─► Alertmanager :9093
                        └─► Grafana :3001 (ops)
```

Sensors publish `RawEvent` on the in-process **raw bus**. `pipeline.py`
enriches it (GeoIP, MITRE, severity, credential counters) onto the **enriched
bus**, where `storage.py` persists and `api.py`/`metrics.py` serve it. No
external broker.

## 2. Ports

| Surface | Port | Audience |
|---|---|---|
| SSH / HTTP honeypots | `8022` / `8081` | attacker |
| Stats API + WebSocket | `8090` | dashboard |
| Metrics exporter | `8000` | Prometheus |
| Dashboard | `3000` | analyst |
| Grafana / Prometheus / Alertmanager | `3001` / `9090` / `9093` | operator |
| PostgreSQL | `127.0.0.1:5432` | backend only |

The dashboard container serves the SPA on `:80` and proxies `/api` and `/ws`
to `backend:8090`, so the browser uses one origin and no CORS. Grafana is on
`3001`; the React console owns `3000`.

## 3. Data ownership

| Store | Owns | Does not own |
|---|---|---|
| PostgreSQL | events (180 d), credential/payload aggregates, GeoIP cache | metrics, dashboards |
| Prometheus | metrics (15 d), alert evaluation | event records, PII as labels |
| React dashboard | threat-intel views: feed, KPIs, chart, map, top credentials/sources, payloads | alerting, long-term storage |
| Grafana | ops dashboards: ingest rate, pipeline/alert health | the analyst threat console |

The product UI answers "who is attacking us and how?"; Grafana answers "is the
pipeline healthy?". Neither is a second source of truth for the other's data.

## 4. Trust boundaries and safety model

- **Attacker input is hostile.** Credentials, paths, commands and user agents
  are data: rendered as text, never HTML or clickable links, never reflected
  unescaped.
- **Hash-only credentials.** Passwords are SHA-256-hashed at the edge; only
  `sha256:<64 hex>` is stored, returned or exported. Plaintext is never logged.
- **No payload execution or fetching.** `wget`/`curl` return a fake success;
  only URL/hash/size metadata is recorded. `CAPTURE_PAYLOADS` (off by default)
  stages bytes in a noexec quarantine for manual review.
- **Containment.** The compose network is a plain bridge (not `internal: true`)
  because the default `ip-api` provider needs egress. Tightening egress
  (allow-list, offline MaxMind, `NullProvider`) is a backend-slice decision.
  The honeypot never connects to attacker-supplied addresses.
- **Ops/product separation.** Prometheus/Alertmanager/Grafana read metrics and
  never write events. The API and dashboard are unauthenticated in v1 and must
  stay on localhost or behind a trusted reverse proxy. Grafana anonymous access
  is Viewer-only in the demo.

## 5. Monitoring flow

```
backend metrics.py (:8000)
        │ scrape every 15s
        ▼
Prometheus (:9090) ── evaluates monitoring/prometheus/rules/alerts.yml
        │                        │
        │ query                  ▼
        ▼                 Alertmanager (:9093) ──► notification
Grafana (:3001)
  3 dashboards: Overview · Attack Patterns · Pipeline Health
```

Prometheus is the **single alerting authority**. The backend exports metrics
only; it does not push alerts, and `backend/alerts.py` is deferred. Thresholds
live in `monitoring/prometheus/rules/alerts.yml`. The React geographic map is
independent of Grafana — Grafana ships no geo map in v1.

## 6. Failure behaviour

- **PostgreSQL down:** API returns `503 {error, detail}`; the dashboard keeps
  its last snapshot, shows a degraded banner, and reconnects with backoff.
- **Backend down:** nginx still serves the SPA; `/api` and `/ws` fail, and
  Prometheus marks the target down and alerts.
- **Monitoring configs absent:** bind-mounted directories make services start
  but report config errors until the monitoring slice lands.

See `docs/API.md` for endpoint shapes, error codes and metric families.
