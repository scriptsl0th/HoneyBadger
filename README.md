# 🍯 HoneyBadger

A self-contained network honeypot suite: a **custom-built SSH and HTTP honeypot** in Python that captures attacker activity, auto-classifies it against **MITRE ATT&CK**, and streams the results to a **React dashboard** with a full observability stack — all deployed with **docker-compose**.

> Built from scratch. No Cowrie, no K8s, no external brokers. One asyncio process, one event pipeline, one `docker-compose up`.

---

## Highlights

- **Custom SSH emulation** (`asyncssh`) with an interactive fake shell that intercepts `wget`/`curl` — attackers get believable responses, we get the payload **metadata only**.
- **Two-stage async event bus**: raw events → enrichment pipeline (GeoIP, MITRE, credential extraction) → enriched events → dashboard.
- **ATT&CK-native**: every event auto-tagged (T1110 brute force, T1595 scanning, T1105 tool transfer, …); the attack simulator *asserts* those tags in tests.
- **Safety by design**: passwords stored as **hashes only**, payloads never fetched or executed, honeypot network isolated, no backdoor to the host.
- **Real-time dashboard** (React + Vite): live WebSocket event feed + REST aggregates + geographic map.
- **Full observability**: Prometheus metrics, curated alert rules, provisioned Grafana dashboards.
- **One-command stack**: PostgreSQL, backend, dashboard, Prometheus, Alertmanager, Grafana — so `docker-compose up` gets you a live, demoable system.

## Architecture at a glance

```
Attacker ──► sshd.py ──► fakeshell.py ─┐
Attacker ──► httpd.py ──► http_routes.py ─┤  raw bus ─► pipeline.py ─► Postgres
                                          │                ├─ geoip.py
                                          │                ├─ mitre.py
                                          │                └─ credentials.py
                                          └── enriched bus ─► api.py ──► dashboard
                                                                └── metrics.py ─► Prometheus ─► Grafana
```

See **[SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md)** for design rationale and diagrams, and **[REPO_STRUCTURE.md](REPO_STRUCTURE.md)** for the full layout.

## Quick start

```bash
git clone https://github.com/yourusername/honeybadger.git
cd honeybadger
docker-compose up -d
```

Then point your browser at `http://localhost:3000` → send traffic at ports **8022** (SSH) and **8081** (HTTP) — or run the bundled attack simulator to seed it:

```bash
docker-compose exec backend python -m sim.simulate
```

| Service | URL |
|---|---|
| Dashboard | `http://localhost:3000` |
| Intake API | `http://localhost:8090` |
| Prometheus | `http://localhost:9090` |
| Grafana | `http://localhost:3000/grafana` |

## Safety first

This project is designed to be harmless, on purpose:

- **No plaintext credentials** — only SHA-256 hashes and aggregates are persisted.
- **No malware execution** — payloads are recorded as URL + hash only; optional (off-by-default) noexec quarantine for manual review.
- **No internet egress** from the honeypot network.
- Read the ethics + handling notes in **[docs/RESPONSIBLE_DISCLOSURE.md](docs/RESPONSIBLE_DISCLOSURE.md)**.

## Roadmap

- [ ] Week 1 — Skeleton: compose, intake contract (`POST /v1/events`), Vite scaffold
- [ ] Week 2 — SSH + fake shell (incl. `wget`/`curl` interception)
- [ ] Week 3 — HTTP sensor + bait routes + two-stage bus end-to-end
- [ ] Week 4 — Pipeline: GeoIP, MITRE, credentials, PostgreSQL, retention, simulator v1
- [ ] Week 5 — React dashboard (live feed + stats + map)
- [ ] Week 6 — Observability: metrics, alerts, Grafana
- [ ] Week 7 — Hardening + docs + demo run

## License

MIT