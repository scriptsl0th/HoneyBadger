#!/usr/bin/env bash
# HoneyBadger Attack Scenario Test Runner
# Runs the attack scenario tests against a docker-compose stack

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# Default configuration
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.yml"
COMPOSE_PROJECT_NAME="hb-test"
SSH_HOST="127.0.0.1"
SSH_PORT="8022"
HTTP_HOST="127.0.0.1"
HTTP_PORT="8081"
API_HOST="127.0.0.1"
API_PORT="8090"
DB_DSN="postgresql://honeybadger:honeybadger@localhost:15432/honeybadger"
SCENARIOS=""
OUTPUT_FILE=""
VERBOSE=false
CLEANUP_ON_EXIT=true
WAIT_FOR_HEALTH=true
HEALTH_TIMEOUT=120

usage() {
    cat <<EOF
Usage: $0 [OPTIONS]

Run HoneyBadger attack scenario tests against a docker-compose stack.

OPTIONS:
    -s, --scenarios LIST      Comma-separated list of scenarios to run (default: all)
    --ssh-host HOST           SSH honeypot host (default: 127.0.0.1)
    --ssh-port PORT           SSH honeypot port (default: 8022)
    --http-host HOST          HTTP honeypot host (default: 127.0.0.1)
    --http-port PORT          HTTP honeypot port (default: 8081)
    --api-host HOST           API host (default: 127.0.0.1)
    --api-port PORT           API port (default: 8090)
    --db-dsn DSN              PostgreSQL DSN (default: postgresql://honeybadger:honeybadger@localhost:15432/honeybadger)
    -o, --output FILE         Output JSON results file
    -v, --verbose             Verbose logging
    --no-cleanup              Don't stop containers after test
    --no-wait-health          Don't wait for health checks
    --health-timeout SEC      Health check timeout in seconds (default: 120)
    -h, --help                Show this help

SCENARIOS:
    ssh_credential_stuffing   T1110.004 - SSH credential stuffing
    ssh_brute_force           T1110 - SSH brute force / password spraying
    ssh_payload_download      T1105 - SSH wget/curl payload downloads
    ssh_post_exploitation     T1059, T1078 - SSH post-exploitation commands
    http_web_scanning         T1595 - HTTP web scanning / reconnaissance
    http_exploit_attempts     T1190 - HTTP exploit attempts (SQLi, RCE, etc.)
    http_credential_capture   T1110 - HTTP login credential capture
    mitre_classification      Verify MITRE ATT&CK classification accuracy
    geoip_enrichment          Verify GeoIP enrichment
    payload_tracking          Verify payload metadata tracking
    api_endpoints             Verify API endpoints
    websocket_stream          Verify WebSocket event streaming
    retention_purge           Verify retention manager

EXAMPLES:
    # Run all scenarios against local stack
    $0

    # Run specific scenarios
    $0 --scenarios ssh_brute_force,http_exploit_attempts

    # Run against remote stack
    $0 --ssh-host 10.0.0.5 --http-host 10.0.0.5 --api-host 10.0.0.5

    # Save results to file
    $0 -o results.json

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--scenarios)
            SCENARIOS="$2"
            shift 2
            ;;
        --ssh-host)
            SSH_HOST="$2"
            shift 2
            ;;
        --ssh-port)
            SSH_PORT="$2"
            shift 2
            ;;
        --http-host)
            HTTP_HOST="$2"
            shift 2
            ;;
        --http-port)
            HTTP_PORT="$2"
            shift 2
            ;;
        --api-host)
            API_HOST="$2"
            shift 2
            ;;
        --api-port)
            API_PORT="$2"
            shift 2
            ;;
        --db-dsn)
            DB_DSN="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --no-cleanup)
            CLEANUP_ON_EXIT=false
            shift
            ;;
        --no-wait-health)
            WAIT_FOR_HEALTH=false
            shift
            ;;
        --health-timeout)
            HEALTH_TIMEOUT="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    log_error "docker-compose not found. Please install Docker Compose."
    exit 1
fi

COMPOSE_CMD="docker-compose"
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
fi

# Start the stack if not already running
start_stack() {
    log_info "Starting HoneyBadger stack..."

    # Check if services are already running
    if $COMPOSE_CMD -f "$COMPOSE_FILE" -p "$COMPOSE_PROJECT_NAME" ps --services --filter "status=running" 2>/dev/null | grep -q .; then
        log_info "Stack appears to be already running"
        return 0
    fi

    $COMPOSE_CMD -f "$COMPOSE_FILE" -p "$COMPOSE_PROJECT_NAME" up -d

    if [[ "$WAIT_FOR_HEALTH" == "true" ]]; then
        log_info "Waiting for services to become healthy (timeout: ${HEALTH_TIMEOUT}s)..."
        local start_time=$(date +%s)
        local all_healthy=false

        while [[ $(($(date +%s) - start_time)) -lt $HEALTH_TIMEOUT ]]; do
            # Check backend health
            if curl -sf "http://${API_HOST}:${API_PORT}/health" > /dev/null 2>&1; then
                all_healthy=true
                break
            fi
            sleep 2
        done

        if [[ "$all_healthy" != "true" ]]; then
            log_error "Services did not become healthy within ${HEALTH_TIMEOUT}s"
            $COMPOSE_CMD -f "$COMPOSE_FILE" -p "$COMPOSE_PROJECT_NAME" logs --tail=50
            return 1
        fi

        log_success "All services healthy"
    fi
}

# Stop the stack
stop_stack() {
    if [[ "$CLEANUP_ON_EXIT" == "true" ]]; then
        log_info "Stopping HoneyBadger stack..."
        $COMPOSE_CMD -f "$COMPOSE_FILE" -p "$COMPOSE_PROJECT_NAME" down -v
        log_success "Stack stopped"
    else
        log_info "Skipping cleanup (--no-cleanup specified)"
    fi
}

# Run the attack scenario tests
run_tests() {
    log_info "Running attack scenario tests..."

    # Build test arguments
    TEST_ARGS=(
        "--ssh-host" "$SSH_HOST"
        "--ssh-port" "$SSH_PORT"
        "--http-host" "$HTTP_HOST"
        "--http-port" "$HTTP_PORT"
        "--api-host" "$API_HOST"
        "--api-port" "$API_PORT"
        "--db-dsn" "$DB_DSN"
    )

    if [[ -n "$SCENARIOS" ]]; then
        IFS=',' read -ra SCENARIO_ARRAY <<< "$SCENARIOS"
        TEST_ARGS+=("--scenarios" "${SCENARIO_ARRAY[@]}")
    fi

    if [[ -n "$OUTPUT_FILE" ]]; then
        TEST_ARGS+=("--output" "$OUTPUT_FILE")
    fi

    if [[ "$VERBOSE" == "true" ]]; then
        TEST_ARGS+=("--verbose")
    fi

    # Run the test script
    # We need to run it in a container with the test dependencies
    log_info "Executing: python3 ${SCRIPT_DIR}/attack_scenarios.py ${TEST_ARGS[*]}"

    # Check if we can run locally (dependencies installed)
    if python3 -c "import aiohttp, asyncssh, psycopg2" 2>/dev/null; then
        python3 "${SCRIPT_DIR}/attack_scenarios.py" "${TEST_ARGS[@]}"
    else
        log_info "Dependencies not found locally, running in test container..."
        $COMPOSE_CMD -f "$COMPOSE_FILE" -p "$COMPOSE_PROJECT_NAME" run --rm \
            -e PYTHONPATH=/app \
            -v "${PROJECT_ROOT}:/app" \
            -w /app \
            backend \
            python3 tests/attack_scenarios.py "${TEST_ARGS[@]}"
    fi
}

# Main execution
main() {
    log_info "HoneyBadger Attack Scenario Test Runner"
    log_info "Project root: $PROJECT_ROOT"

    # Trap for cleanup
    trap stop_stack EXIT

    # Start stack
    if ! start_stack; then
        log_error "Failed to start stack"
        exit 1
    fi

    # Run tests
    if run_tests; then
        log_success "All attack scenario tests passed!"
        exit 0
    else
        log_error "Some attack scenario tests failed"
        exit 1
    fi
}

main "$@"