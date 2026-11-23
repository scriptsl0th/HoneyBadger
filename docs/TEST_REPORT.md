# Test report

Date: 2026-11-21. Base commit: `93a9d69` (`main` after PR #2). All changes described here are on branch `presentation-prep`.

Every result below was produced by a command that was actually run. Where something could not be run, this report says so.

## Environment

| Item | Version or detail |
|---|---|
| OS | Linux container (x86-64) |
| Python | 3.13 (backend tests), plus a second environment with pandas 2.2.3 / scikit-learn 1.6.1 (Colab-like) for the notebooks |
| PostgreSQL | 16.15, started locally on port 15432, schema created with `alembic upgrade head` |
| Node.js | 22 |
| Docker | Client and Compose v5.7.1 present, **no Docker daemon**: containers could not be started |

Because Docker could not run, the whole stack was run **without Docker**: PostgreSQL, the backend (`python main.py`: SSH, HTTP, API, metrics, pipeline) and the dashboard dev server, on the same ports as the Compose stack. Prometheus, Grafana and Alertmanager were not started.

## Summary

| Area | Before the fixes | After the fixes |
|---|---|---|
| Backend `pytest` (default run) | **Did not run**: 3 collection errors, 0 tests executed | **90 passed, 7 skipped** (API tests skip without a database) |
| Backend `pytest` with a test database | Did not run | **97 passed** |
| Live attack scenarios (`tests/attack_scenarios.py`, 13 scenarios) | 7 passed, 6 failed | **10 passed, 3 failed** (see "Remaining failures") |
| Backend errors during the live run | 10 tracebacks (8 pipeline `NameError`, 2 HTTP 500) | **0** |
| Simulator (`python -m sim.simulate`) | Stub: slept and sent nothing | Sends 8/8 SSH attacks and 6/6 HTTP probes, prints the recorded techniques |
| Dashboard tests (`npm test`) | 25 passed | 25 passed |
| Dashboard build (`npm run build`, includes type check) | Passed | Passed (bundle-size warning only) |
| Dashboard against the live API | Activity chart broken ("Volume per NaN min", empty chart) | Chart shows real buckets (screenshot below) |
| Analysis notebooks (`scripts/run_analysis.py`) | No automated check existed | **50/50 checks passed**, on two library generations |
| Plaintext passwords in the database | Not checked | **0** found in a full database dump |
| `docker compose config` | Not checked | Valid; 6 services |

## How each test was run

### 1. Backend unit and API tests

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r backend/requirements-dev.txt
pytest                                    # 90 passed, 7 skipped
HB_TEST_DATABASE_URL=postgresql+asyncpg://honeybadger:honeybadger@127.0.0.1:15432/honeybadger_test pytest   # 97 passed
```

Before the fixes, `pytest` stopped during collection:

- `backend/tests/test_api.py` imported `EventStore`, which no longer exists: `api.py` had moved to PostgreSQL and the test had not been updated.
- `backend/tests/test_simulate.py` expected `build_attack` and `make_parser` in `sim/simulate.py`, which was a stub.
- `tests/test_attack_scenarios.py` could not import its own helper module, and needs `pytest-asyncio`, which no requirements file installs.

### 2. Live system

```bash
# terminal 1: database (any PostgreSQL 14+ works; Docker users: docker compose up -d postgres)
# terminal 2: backend
cd backend
alembic upgrade head
HB_DATABASE_URL=postgresql+asyncpg://honeybadger:honeybadger@127.0.0.1:15432/honeybadger python main.py
# terminal 3: the team's scenario runner
PYTHONPATH=backend python tests/attack_scenarios.py --db-dsn postgresql://honeybadger:honeybadger@127.0.0.1:15432/honeybadger
```

| Scenario | Before | After | Note |
|---|---|---|---|
| ssh_credential_stuffing | FAIL | PASS | The test counted command events as logins (test fix) |
| ssh_brute_force | FAIL | FAIL | Definition question, see below |
| ssh_payload_download | FAIL | PASS | Pipeline crash fixed |
| ssh_post_exploitation | PASS | PASS | |
| http_web_scanning | PASS | PASS | |
| http_exploit_attempts | FAIL | PASS | Query string is now recorded and classified |
| http_credential_capture | FAIL | FAIL | Definition question, see below |
| mitre_classification | FAIL | FAIL | T1078 is never produced, see below |
| geoip_enrichment | PASS | PASS | Local traffic (127.0.0.1) has no location; this is expected |
| payload_tracking | PASS | PASS | Payload URLs recorded; nothing downloaded (by design) |
| api_endpoints | PASS | PASS | 10/10 endpoints |
| websocket_stream | PASS | PASS | |
| retention_purge | PASS | PASS | |

### 3. Simulator

```bash
cd backend
python -m sim.simulate --count 8 --delay 0.1
```

Measured output (fresh database):

```text
Sent 8 of 8 SSH attacks (16 commands) and 6 of 6 HTTP probes.
Events recorded since the run started, by MITRE technique:
  T1059      12
  T1110.004  5
  T1105      4
  T1110      4
  T1595      3
  T1190      2
```

### 4. Security checks

- **No plaintext passwords stored.** After the simulator run, a full `pg_dump` of the database contained 0 occurrences of the passwords used (`123456`, `raspberry`, `password123`). Logins are stored as `sha256:` hashes.
- **Passwords in URLs are redacted.** `GET /login?user=admin&pwd=hunter2` is stored as `/login?user=admin&pwd=REDACTED` (test `test_password_in_query_string_is_redacted`).
- **Payloads are never fetched.** `wget`/`curl` commands produce fake output; payload rows have no hash and no size (scenario `payload_tracking`).

### 5. Dashboard

```bash
cd dashboard
npm ci && npm test && npm run build
npx vite --host 127.0.0.1     # proxies /api and /ws to the backend on :8090
```

With the backend running and the simulator sending traffic, the page loaded with no script errors and showed the events, the ATT&CK coverage and the activity chart:

![Dashboard with live data](img/dashboard_live.png)

### 6. Analysis notebooks

```bash
pip install -r requirements-analysis.txt
python scripts/run_analysis.py
```

The script executes `notebooks/pair1_attack_classification.ipynb`, `pair2_anomaly_detection.ipynb` and `pair3_attack_profiling.ipynb` (from inside `notebooks/`), reads their `results/pair*_results.json` files, and compares 74 key numbers with `scripts/expected_results.json`. Those reference values are the numbers reported to the group before this run.

| Environment | Pair 1 | Pair 2 | Run time |
|---|---|---|---|
| pandas 3.0.5, scikit-learn 1.9.1 | 26/26 | 24/24 | 68 s + 20 s |
| pandas 2.2.3, scikit-learn 1.6.1 (Colab-like) | 26/26 | 24/24 | 80 s + 19 s |

Pair 3 was added later and checked with pandas 3.1.1, scikit-learn 1.9.1, Python 3.13: 24/24 checks, about 160 s, identical numbers on two consecutive runs. It has not yet been run with scikit-learn 1.6.

In Google Colab, only `intrusion_analysis.ipynb` has been run so far (2026-11-19, identical results). The Pair 1 and Pair 2 notebooks have not been checked in Colab itself; the second environment above uses the same library versions as Colab.

## Bugs found and fixed

| # | Bug | Effect | Fix | Test |
|---|---|---|---|---|
| 1 | `pipeline.py` used `record_payload_captured` without importing it | Every payload event logged a pipeline error and skipped its metrics | Import added | `test_payload_event_is_stored_published_and_counted` |
| 2 | `POST /phpmyadmin` route passed the request to a function that takes none | HTTP 500 for every phpMyAdmin login attempt | Route fixed | `test_phpmyadmin_login_post_does_not_crash` |
| 3 | The HTTP sensor stored `request.path` without the query string | `/?id=1' OR 1=1--` was stored as `/`: exploit evidence lost, T1190 missed | Query string stored (URL-decoded), secret parameters redacted, length capped at 2,048 | `test_query_string_is_recorded_so_exploits_are_classified` |
| 4 | Classifier checked scanner paths before credentials | `POST /admin` with a username and password was tagged T1595 (scan) | Credential rule moved before the scanner rule | `test_login_post_with_credentials_is_a_credential_attack_not_a_scan` |
| 5 | `/events` and the WebSocket served SSH handshake rows | Feed filled with untagged rows that carry no attacker action | Handshakes filtered in the query and the broadcast (still stored) | `test_handshake_events_stay_off_the_feed`, WebSocket test |
| 6 | `/stats/timeseries` returned a bare list; the dashboard expects `{window, bucket_seconds, points}` | Activity chart empty, "Volume per NaN min" | Response wrapped in the documented shape; `/stats` `window` returned as `1h` | `test_timeseries_returns_aligned_buckets` |
| 7 | `sim/simulate.py` was a stub | README commands did nothing | Simulator implemented | `test_simulate.py`, live run |
| 8 | Test tooling: wrong import paths, missing `psycopg2`, Dockerfile.test `PYTHONPATH`, handshake rows counted as attacks | Live tests could not run or under-counted | Paths, requirement and counting fixed; live pytest file skips cleanly when the stack is down | Live run |

## Remaining failures and known gaps

1. **Brute force vs credential stuffing (2 scenarios).** The test expects one username with many passwords to be T1110 (brute force). The classifier tags every login whose username is common (`root`, `admin`...) as T1110.004 (credential stuffing). The README defines T1110.004 a third way: "repeated same-credential attempts". This is a design decision for the team. A correct fix needs per-source history (for example: many passwords for one username → T1110; known username:password pairs across many usernames → T1110.004).
2. **T1078 (Valid Accounts) is never produced.** Every login matches a T1110 rule first, so the T1078 rule is unreachable. Decide whether to drop T1078 from the documentation or tag sessions after login.
3. **Placeholder tests.** `tests/integration/test_end_to_end.sh`, `tests/integration/test_api_contract.py`, `tests/security/test_network_isolation.sh` and `tests/security/test_credentials.sh` are empty files. Their goals are partly covered by `backend/tests/test_api.py`, `backend/tests/test_httpd.py` and the live scenarios.
4. **Not run here:** the Docker Compose stack, Prometheus, Grafana and Alertmanager (no Docker daemon). The Compose file was only validated with `docker compose config`.
5. **Source IP trust.** The HTTP sensor takes the client IP from `X-Forwarded-For` when present. An attacker can set that header and fake their address. This is fine behind a trusted proxy, misleading otherwise.
6. **GeoIP** returns nothing for local traffic (expected) and was not tested with public IPs, because this environment has no access to `ip-api.com`.
7. **Statistics include handshakes.** `/stats` totals still count SSH handshake rows, while the feed hides them. Numbers on the KPI tiles are therefore higher than the number of rows in the feed.
