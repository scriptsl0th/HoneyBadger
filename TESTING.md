# HoneyBadger Testing Guide

Complete guide for running unit tests, attack scenario tests, and integration tests.

---

## Quick Start

```bash
# 1. Start the full stack
docker-compose up -d

# 2. Wait for backend health check (10-30 seconds)
curl http://localhost:8090/health
# {"status":"ok","db":"ok","version":"0.2.0","uptime_s":...}

# 3. Run all attack scenarios
docker-compose run --rm -v "${PWD}:/app" -w /app backend python tests/attack_scenarios.py

# 4. Run unit tests
docker-compose run --rm backend python -m pytest backend/tests -v
```

---

## Test Categories

| Category | Command | Description |
|----------|---------|-------------|
| **Unit Tests** | `make test-unit` | Fast, isolated backend tests (schemas, bus, fakeshell, config, ssh handshake) |
| **Attack Scenarios** | `make test-attack` | Full attack simulation against live honeypots |
| **SSH Attacks Only** | `make test-attack-ssh` | Credential stuffing, brute force, payload download, post-exploitation |
| **HTTP Attacks Only** | `make test-attack-http` | Web scanning, exploit attempts, credential capture |
| **Verification** | `make test-attack-mitre` | MITRE classification, GeoIP, payload tracking |
| **Integration** | `make test-integration` | Pytest-style tests with assertions |
| **All Tests** | `make test` | Unit + attack scenarios |

---

## Running Attack Scenarios

### Basic Usage

```bash
# Run all scenarios (default)
docker-compose run --rm -v "${PWD}:/app" -w /app backend python tests/attack_scenarios.py

# Run specific scenarios
docker-compose run --rm -v "${PWD}:/app" -w /app backend python tests/attack_scenarios.py \
  --scenarios ssh_brute_force,http_exploit_attempts

# Save results to JSON
docker-compose run --rm -v "${PWD}:/app" -w /app backend python tests/attack_scenarios.py \
  --output results.json

# Verbose output
docker-compose run --rm -v "${PWD}:/app" -w /app backend python tests/attack_scenarios.py -v
```

### Available Scenarios

| Scenario | MITRE Technique | Description |
|----------|-----------------|-------------|
| `ssh_credential_stuffing` | T1110.004 | Common username/password pairs |
| `ssh_brute_force` | T1110 | Password spraying against root |
| `ssh_payload_download` | T1105 | wget/curl malicious URLs |
| `ssh_post_exploitation` | T1059, T1078 | Shell commands after auth |
| `http_web_scanning` | T1595 | 30+ scanner paths (/.env, /wp-admin, etc.) |
| `http_exploit_attempts` | T1190 | SQLi, RCE, path traversal, Log4Shell, etc. |
| `http_credential_capture` | T1110 | Login form submissions |
| `mitre_classification` | — | Verify all 7 techniques detected |
| `geoip_enrichment` | — | Verify IP geolocation enrichment |
| `payload_tracking` | — | Verify payload URL/hash/size capture |
| `api_endpoints` | — | Verify REST API health/stats/events |
| `websocket_stream` | — | Verify live event streaming |
| `retention_purge` | — | Verify retention data structures |

### Custom Target (Remote Stack)

```bash
docker-compose run --rm -v "${PWD}:/app" -w /app backend python tests/attack_scenarios.py \
  --ssh-host 10.0.0.5 --ssh-port 8022 \
  --http-host 10.0.0.5 --http-port 8081 \
  --api-host 10.0.0.5 --api-port 8090 \
  --db-dsn "postgresql://user:pass@10.0.0.5:5432/honeybadger"
```

---

## Attack Count Configuration

### Environment Variables

```bash
docker-compose run --rm -v "${PWD}:/app" -w /app backend \
  -e ATTACK_CREDENTIAL_PAIRS=30 \
  -e ATTACK_BRUTE_FORCE_PASSWORDS=25 \
  -e ATTACK_PAYLOAD_URLS=15 \
  -e ATTACK_POST_EXPLOIT_CMDS=20 \
  -e ATTACK_SCANNER_PATHS=50 \
  -e ATTACK_EXPLOIT_PAYLOADS=30 \
  -e ATTACK_LOGIN_ATTEMPTS=15 \
  python tests/attack_scenarios.py
```

| Variable | Default | Description |
|----------|---------|-------------|
| `ATTACK_CREDENTIAL_PAIRS` | 10 | SSH credential stuffing pairs |
| `ATTACK_BRUTE_FORCE_PASSWORDS` | 10 | SSH brute force passwords |
| `ATTACK_PAYLOAD_URLS` | 4 | Payload download URLs |
| `ATTACK_POST_EXPLOIT_CMDS` | 10 | Post-exploitation commands |
| `ATTACK_SCANNER_PATHS` | 33 | HTTP scanner paths |
| `ATTACK_EXPLOIT_PAYLOADS` | 18 | HTTP exploit payloads |
| `ATTACK_LOGIN_ATTEMPTS` | 7 | HTTP login attempts |

### Command-Line Arguments

```bash
docker-compose run --rm -v "${PWD}:/app" -w /app backend python tests/attack_scenarios.py \
  --credential-pairs 30 \
  --brute-passwords 25 \
  --payload-urls 15 \
  --post-exploit-cmds 20 \
  --scanner-paths 50 \
  --exploit-payloads 30 \
  --login-attempts 15
```

### Config File (YAML)

Create `tests/attack_config.yaml`:
```yaml
scenarios:
  ssh_credential_stuffing:
    credential_pairs: 30
  ssh_brute_force:
    passwords: 25
  ssh_payload_download:
    urls: 15
  ssh_post_exploitation:
    commands: 20
  http_web_scanning:
    paths: 50
  http_exploit_attempts:
    payloads: 30
  http_credential_capture:
    attempts: 15
```

Run with:
```bash
docker-compose run --rm -v "${PWD}:/app" -w /app backend \
  python tests/attack_scenarios.py --config tests/attack_config.yaml
```

---

## Running with Test Runner Script

The `tests/run_attack_scenarios.sh` script handles stack startup/teardown automatically:

```bash
# Run all scenarios (starts stack if needed)
./tests/run_attack_scenarios.sh

# Run specific scenarios
./tests/run_attack_scenarios.sh --scenarios ssh_brute_force,http_exploit_attempts

# Don't cleanup after (keep stack running)
./tests/run_attack_scenarios.sh --no-cleanup

# Custom ports
./tests/run_attack_scenarios.sh --ssh-port 2222 --http-port 8080 --api-port 8090

# Verbose with output file
./tests/run_attack_scenarios.sh -v -o results.json
```

### Script Options

| Option | Description |
|--------|-------------|
| `-s, --scenarios LIST` | Comma-separated scenarios |
| `--ssh-host/port` | SSH target |
| `--http-host/port` | HTTP target |
| `--api-host/port` | API target |
| `--db-dsn` | PostgreSQL DSN |
| `-o, --output FILE` | JSON output file |
| `-v, --verbose` | Verbose logging |
| `--no-cleanup` | Keep containers running |
| `--no-wait-health` | Skip health check wait |
| `--health-timeout SEC` | Health check timeout (default 120s) |

---

## Pytest Integration (CI/CD)

```bash
# Run all attack scenario tests
docker-compose run --rm backend python -m pytest tests/test_attack_scenarios.py -v

# Run specific test class
docker-compose run --rm backend python -m pytest tests/test_attack_scenarios.py -v -k "ssh"

# Run with coverage
docker-compose run --rm backend python -m pytest tests/test_attack_scenarios.py --cov=backend -v

# JUnit XML for CI
docker-compose run --rm backend python -m pytest tests/test_attack_scenarios.py --junitxml=test-results.xml
```

### Pytest Markers

```bash
# SSH tests only
pytest -k "ssh" -v

# HTTP tests only
pytest -k "http" -v

# MITRE verification tests
pytest -k "mitre" -v

# Full attack chain
pytest tests/test_attack_scenarios.py::test_full_attack_chain -v
```

---

## Expected Test Output

### Successful Run

```
============================================================
ATTACK SCENARIO TEST SUMMARY
============================================================
Overall: PASSED
Scenarios run: 13
  ssh_credential_stuffing: PASS
  ssh_brute_force: PASS
  ssh_payload_download: PASS
  ssh_post_exploitation: PASS
  http_web_scanning: PASS
  http_exploit_attempts: PASS
  http_credential_capture: PASS
  mitre_classification: PASS
  geoip_enrichment: PASS
  payload_tracking: PASS
  api_endpoints: PASS
  websocket_stream: PASS
  retention_purge: PASS
============================================================
```

### Sample JSON Output (`--output results.json`)

```json
{
  "started_at": "2026-11-10T12:00:00+00:00",
  "scenarios_run": ["ssh_credential_stuffing", "..."],
  "results": {
    "ssh_credential_stuffing": {
      "scenario": "credential_stuffing",
      "technique": "T1110.004",
      "events_captured": 10,
      "credential_stuffing_events": 9,
      "classification_correct": true,
      "tests": [...]
    }
  },
  "overall_passed": true,
  "completed_at": "2026-11-10T12:02:30+00:00"
}
```

---

## Troubleshooting

### Backend Not Healthy

```bash
# Check logs
docker-compose logs backend

# Check database connectivity
docker-compose exec postgres pg_isready -U honeybadger

# Restart backend
docker-compose restart backend
```

### Connection Refused

```bash
# Verify ports are mapped
docker-compose ps

# Test connectivity
curl http://localhost:8090/health
nc -zv localhost 8022
nc -zv localhost 8081
```

### Tests Timeout

```bash
# Increase health check timeout
./tests/run_attack_scenarios.sh --health-timeout 300

# Or run with longer timeout in docker
docker-compose run --rm -v "${PWD}:/app" -w /app backend \
  python tests/attack_scenarios.py --scenarios ssh_brute_force
```

### Database Errors

```bash
# Check database state
docker-compose exec postgres psql -U honeybadger -d honeybadger -c "SELECT COUNT(*) FROM events;"

# Reset database
docker-compose down -v
docker-compose up -d
```

---

## CI/CD Pipeline Example

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: Attack Scenario Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: honeybadger
          POSTGRES_PASSWORD: honeybadger
          POSTGRES_DB: honeybadger
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U honeybadger"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10

    steps:
      - uses: actions/checkout@v4

      - name: Start stack
        run: docker-compose up -d

      - name: Wait for backend
        run: |
          for i in {1..30}; do
            curl -sf http://localhost:8090/health && break
            sleep 2
          done

      - name: Run attack scenarios
        run: |
          docker-compose run --rm -v "${PWD}:/app" -w /app backend \
            python tests/attack_scenarios.py --output results.json

      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: attack-test-results
          path: results.json
```

---

## Port Reference

| Service | Host Port | Container Port | Protocol |
|---------|-----------|----------------|----------|
| SSH Honeypot | 8022 | 8022 | TCP |
| HTTP Honeypot | 8081 | 8081 | TCP |
| API + WebSocket | 8090 | 8090 | TCP |
| Prometheus Metrics | 8000 | 8000 | TCP |
| PostgreSQL | 15432 | 5432 | TCP |
| Dashboard | 3000 | 80 | TCP |
| Grafana | 3001 | 3000 | TCP |
| Prometheus | 9090 | 9090 | TCP |
| Alertmanager | 9093 | 9093 | TCP |

---

## Files Created

```
tests/
├── attack_scenarios.py          # Main test runner
├── test_attack_scenarios.py     # Pytest-compatible tests
├── run_attack_scenarios.sh      # Docker-aware runner script
├── Dockerfile.test              # Test container image
├── attack_config.yaml           # Optional config file
└── integration/
    ├── test_api_contract.py     # Empty placeholder
    └── test_end_to_end.sh       # Empty placeholder
```