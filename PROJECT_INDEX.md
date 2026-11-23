# HoneyBadger project index

Reviewed commit: `93a9d69` (`main` after PR #2) plus the `presentation-prep` changes listed in `CHANGELOG.md`.
Index updated 2026-11-21. Every path below exists in that working tree.

## What the project is

HoneyBadger is a self-contained honeypot. A fake SSH server (port 8022) and a fake
HTTP site (port 8081) accept attacker traffic. Each interaction becomes one event.
The event is enriched with GeoIP and a rule-based MITRE ATT&CK technique, stored in
PostgreSQL, streamed to a React dashboard over WebSocket, and exported as Prometheus
metrics for Grafana and Alertmanager. Everything runs from `docker-compose.yml`.
Passwords are stored only as `sha256:<hex>` hashes, and payload URLs are never fetched.

## Main entry points

| Purpose | Path |
|---|---|
| Stack definition and ports | `docker-compose.yml`, `.env.example` |
| Backend process entry point (wires buses, pipeline, listeners, API) | `backend/main.py` |
| Settings (`HB_*` environment variables) | `backend/config.py` |
| Event contract (`RawEvent`, `EnrichedEvent`, `EventOut`) | `backend/schemas.py` |
| SSH sensor and fake shell | `backend/sshd.py`, `backend/fakeshell.py` |
| HTTP sensor and bait pages | `backend/httpd.py`, `backend/http_routes.py` |
| In-process event bus | `backend/bus.py` |
| Enrichment pipeline | `backend/pipeline.py` |
| Enrichers | `backend/geoip.py`, `backend/mitre.py`, `backend/credentials.py`, `backend/payloads.py` |
| Persistence | `backend/storage.py`, `backend/db/models.py`, `backend/db/migrations/versions/001_initial_schema.py` |
| REST + WebSocket API (`/health`, `/events`, `/stats`, `/stats/timeseries`, `/ws/events`) | `backend/api.py` |
| Prometheus exporter and retention job | `backend/metrics.py`, `backend/retention.py` |
| Dashboard entry point and event types | `dashboard/src/app.tsx`, `dashboard/src/types.ts` |
| Dashboard data access | `dashboard/src/api/endpoints.ts`, `dashboard/src/ws/client.ts`, `dashboard/src/hooks/useLiveEvents.ts` |
| Monitoring config | `monitoring/prometheus/prometheus.yml`, `monitoring/prometheus/rules/alerts.yml`, `monitoring/grafana/dashboards/` |
| Tests | `backend/tests/`, `tests/attack_scenarios.py`, `tests/integration/`, `tests/security/`, `TESTING.md` |
| Design docs | `README.md`, `SYSTEM_ARCHITECTURE.md`, `REPO_STRUCTURE.md`, `docs/ARCHITECTURE.md` |

## Event flow: one SSH or HTTP observation

1. **Collection (SSH).** `SshHoneypotServer` in `backend/sshd.py` handles one TCP connection.
   It publishes up to three kinds of `RawEvent` with `service=ssh`:
   - `event_kind="ssh_handshake"`: client version string, published once per connection.
   - `event_kind="auth"`: from `validate_password()`. The username is kept, the password is
     hashed by `hash_password()`, and every login is accepted.
   - `event_kind="command"`: from `publish_command()` for each line typed in the fake shell
     (`backend/fakeshell.py`). `wget`/`curl` URLs are copied into `payload_url`.
   `RawEvent` rejects SSH events without a username and password hash, except handshakes.
2. **Collection (HTTP).** `HttpHoneypot` in `backend/httpd.py` catches every path. It serves a
   bait page from `select_bait()` in `backend/http_routes.py` or a 404. It extracts and hashes
   form credentials for `POST` to `/login`, `/wp-login.php`, `/phpmyadmin` and `/admin`. It then
   publishes a `RawEvent` with `service=http`, method, path, status, user agent and
   `additional_info={"event_kind": "http_request", "bait_hit": ..., "latency_ms": ...}`.
3. **Raw bus.** Both sensors call `EventBus.publish()` (`backend/bus.py`) on the raw bus created in
   `backend/main.py`. Publishing never blocks the sensor.
4. **Enrichment.** `EnrichmentPipeline._process_event()` in `backend/pipeline.py` runs, in order:
   GeoIP lookup (`backend/geoip.py`, cached in PostgreSQL), `classify()` from `backend/mitre.py`
   (returns `technique_id` and `severity`), credential counters (`backend/credentials.py`) and
   payload metadata (`backend/payloads.py`). It builds an `EnrichedEvent`.
5. **Storage.** `EventRepository.insert()` in `backend/storage.py` writes one row to the `events`
   table (`backend/db/models.py`). The timestamp column is named `ts`; the API exposes it as
   `timestamp`. Geo fields are flattened into columns, and `additional_info` is stored as JSON.
6. **Dashboard.** The pipeline publishes the `EnrichedEvent` to the enriched bus. The
   WebSocket broadcaster in `backend/api.py` sends `{"type": "event", "event": ...}` frames on
   `/ws/events`. The REST endpoints read PostgreSQL. The dashboard (`dashboard/src/app.tsx`)
   backfills with `GET /events`, merges live frames (`dashboard/src/lib/events.ts`) and polls
   `/stats`. `dashboard/src/types.ts::EventOut` mirrors `backend/schemas.py::EventOut`.
7. **Metrics.** `backend/metrics.py` serves Prometheus metrics on `:8000`; Prometheus evaluates
   `monitoring/prometheus/rules/alerts.yml`.

### Stored event fields (what an offline model could use)

`service`, `source_ip`, `destination_ip`, `source_port`, `destination_port`, `ts`, `username`,
`password_hash`, `user_agent`, `http_method`, `http_path`, `http_status_code`, `command`,
`payload_url`, `payload_hash`, `payload_size`, `technique_id`, `severity`, `country`, `region`,
`city`, `latitude`, `longitude`, `asn`, `additional_info`.
There is no per-event ground-truth label, byte count, session duration or session id.

## Where the offline analysis fits

The offline analysis lives in `notebooks/`, `data/` and `results/`, separate from the running stack.
It needs neither Docker nor the honeypot services nor the attack simulator.

| File | Role |
|---|---|
| `notebooks/intrusion_analysis.ipynb` | Colab-ready notebook: data audit, grouped validation, baseline vs. random forest, predictions |
| `data/Train_data.csv` | Kaggle labeled connections (25,192 rows, `class` = `normal`/`anomaly`) |
| `data/Test_data.csv` | Kaggle unlabeled connections (22,544 rows, same 41 features, no `class`) |
| `results/predictions/intrusion_predictions.csv` | Notebook output: one prediction per `Test_data.csv` row, original order |
| `notebooks/pair1_attack_classification.ipynb` | Group objective 1 (supervised attack detection): logistic regression, decision tree and random forest tuned with grouped cross-validation, threshold trade-off, interpretation, feature selection and a HoneyBadger-compatible feature subset |
| `results/predictions/pair1_predictions.csv` | Output of the Pair 1 notebook: one prediction per `Test_data.csv` row, original order |
| `data/prepared/train_prepared.csv`, `validation_prepared.csv`, `test_prepared.csv` | Pair 1 notebook output: the prepared data (constant columns dropped, one-hot encoding fitted on the training partition), with `source_row` back to the original CSV |
| `notebooks/pair2_anomaly_detection.ipynb` | Group objective 2 (detection without labels): Isolation Forest, One-Class SVM and Local Outlier Factor trained on normal traffic only, 1% false-alarm threshold. Siwar and Shayma |
| `results/predictions/pair2_predictions.csv` | Output of the Pair 2 notebook: one anomaly score per `Test_data.csv` row, original order |
| `notebooks/pair3_attack_profiling.ipynb` | Group objective 3 (attack profiling): K-Means, Gaussian Mixture and DBSCAN on the attack rows only, k chosen by elbow, silhouette and Davies-Bouldin, stability checks, family profiles mapped to MITRE ATT&CK as hypotheses, HoneyBadger-compatible feature subset |
| `results/predictions/pair3_predictions.csv` | Output of the Pair 3 notebook: for each `Test_data.csv` row, the predicted class and, for predicted attacks, the family and MITRE hypothesis (not committed) |
| `results/pair1_results.json`, `results/pair2_results.json`, `results/pair3_results.json` | Settings and measured results saved by the notebooks |
| `scripts/run_analysis.py`, `scripts/expected_results.json` | Re-runs the three pair notebooks and checks 74 values against the reference |
| `requirements-analysis.txt` | Python packages for the notebooks and the runner |

The data CSVs, the prepared CSVs and the predictions files are listed in `.gitignore`. The notebooks download or
regenerate them, and the Kaggle license is listed as "Unknown".

Dataset: <https://www.kaggle.com/datasets/sampadab17/network-intrusion-detection>
(publisher Sampada Bhosale; Kaggle lists the license as "Unknown").

| File | Bytes | SHA-256 |
|---|---|---|
| `Train_data.csv` | 2,875,560 | `1e40eb667611ab507870fc5b5ef0a844201ec094915d78d79f4665937e43b07a` |
| `Test_data.csv` | 2,416,180 | `a58db8c605e58411f6432dd9ab2fe10e1d768f058f5453e9e279788c7219caf8` |

The byte sizes match Kaggle's file listing. The checksums were computed locally; the notebook
re-checks them after every download.

A Kaggle row is one network connection summarised by 41 features (KDD-style). A HoneyBadger
row is one application-level event (a login, a command or an HTTP request). The data share
the `service` concept (`ssh`, `http`) but little else. Scores on the Kaggle data therefore do
not measure detection quality on live HoneyBadger events. The notebook's last section maps
the fields and lists the evidence needed for a real evaluation.

## Documentation for the presentation

| File | Content |
|---|---|
| `docs/PROJECT_EXPLAINED_FROM_ZERO.md` | Beginner-to-advanced tutorial with diagrams |
| `docs/DEMO_GUIDE.md` | Executable live demo with expected outputs |
| `docs/RESULTS_AND_ANALYSIS.md` | Measured results and their interpretation |
| `docs/TEST_REPORT.md` | Tests run, before/after results, bugs fixed, open issues |
| `docs/PRESENTATION_SCRIPT.md` | Oral presentation and 2-minute pitch (French) |
| `docs/PROFESSOR_QA.md` | 33 likely questions with answers (French) |
| `docs/FINAL_PROJECT_REPORT.md` | Academic report (French) |

## Gaps noticed while indexing

Fixed on `presentation-prep` (see `CHANGELOG.md`): the pipeline import error, the simulator stub, the README's port and missing-doc links, and the empty `docs/ANALYSIS.md` and `docs/RESPONSIBLE_DISCLOSURE.md`.

Still open:

- `backend/alerts.py` is empty by design (Prometheus owns alerting).
- `tests/integration/` and `tests/security/` hold empty placeholder files.
- Brute force (T1110) vs credential stuffing (T1110.004) is defined differently in the README, `backend/mitre.py` and `tests/attack_scenarios.py`; T1078 is never produced. See `docs/TEST_REPORT.md`.
