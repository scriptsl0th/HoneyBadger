# HoneyBadger Makefile
# Convenience targets for development and testing

.PHONY: help test test-unit test-attack test-attack-ssh test-attack-http test-integration up down logs clean

# Default target
help:
	@echo "HoneyBadger - Available targets:"
	@echo ""
	@echo "  Stack Management:"
	@echo "    up              Start the full stack (docker-compose up -d)"
	@echo "    down            Stop and remove the stack (docker-compose down -v)"
	@echo "    logs            Follow logs from all services"
	@echo "    ps              Show running services"
	@echo ""
	@echo "  Testing:"
	@echo "    test            Run all tests (unit + attack scenarios)"
	@echo "    test-unit       Run unit tests only (backend/tests)"
	@echo "    test-attack     Run all attack scenario tests"
	@echo "    test-attack-ssh Run SSH attack scenarios only"
	@echo "    test-attack-http Run HTTP attack scenarios only"
	@echo "    test-integration Run integration tests"
	@echo ""
	@echo "  Development:"
	@echo "    build           Build all Docker images"
	@echo "    clean           Remove all containers, volumes, and images"
	@echo "    shell-backend   Open shell in backend container"
	@echo "    shell-db        Open psql shell in database"

# Stack management
up:
	docker-compose up -d

down:
	docker-compose down -v

logs:
	docker-compose logs -f

ps:
	docker-compose ps

# Build
build:
	docker-compose build

# Unit tests (run in backend container)
test-unit:
	docker-compose run --rm backend python -m pytest backend/tests -v

# Attack scenario tests
test-attack:
	./tests/run_attack_scenarios.sh

test-attack-ssh:
	./tests/run_attack_scenarios.sh --scenarios ssh_credential_stuffing,ssh_brute_force,ssh_payload_download,ssh_post_exploitation

test-attack-http:
	./tests/run_attack_scenarios.sh --scenarios http_web_scanning,http_exploit_attempts,http_credential_capture

test-attack-mitre:
	./tests/run_attack_scenarios.sh --scenarios mitre_classification,geoip_enrichment,payload_tracking

# Integration tests
test-integration:
	docker-compose run --rm backend python -m pytest tests/test_attack_scenarios.py -v

# Run all tests
test: test-unit test-attack

# Development helpers
shell-backend:
	docker-compose run --rm backend bash

shell-db:
	docker-compose exec postgres psql -U honeybadger -d honeybadger

# Cleanup
clean:
	docker-compose down -v --rmi all --remove-orphans
	docker system prune -f