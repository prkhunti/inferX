.PHONY: help up down build logs logs-api shell-api shell-db migrate db-reset test lint fmt bench \
        dev-up dev-down dev-build dev-logs

COMPOSE     = docker compose -f infra/docker-compose.yml
COMPOSE_DEV = docker compose -f infra/docker-compose.yml -f infra/docker-compose.dev.yml

# Default target
help:
	@echo ""
	@echo "InferX — available commands:"
	@echo ""
	@echo "  Production"
	@echo "    make up           Start all services (prod build)"
	@echo "    make down         Stop all services"
	@echo "    make build        Rebuild all Docker images (no cache)"
	@echo "    make logs         Tail logs from all services"
	@echo "    make logs-api     Tail API logs only"
	@echo ""
	@echo "  Development (hot-reload)"
	@echo "    make dev-up       Start all services with hot-reload"
	@echo "    make dev-down     Stop dev services"
	@echo "    make dev-build    Rebuild dev images"
	@echo "    make dev-logs     Tail dev service logs"
	@echo ""
	@echo "  Database"
	@echo "    make migrate      Run DB migrations"
	@echo "    make db-reset     Drop and recreate the database"
	@echo ""
	@echo "  Dev shells"
	@echo "    make shell-api    Open shell inside API container"
	@echo "    make shell-db     Open psql inside postgres container"
	@echo ""
	@echo "  Quality"
	@echo "    make test         Run all tests"
	@echo "    make lint         Run linters (ruff)"
	@echo "    make fmt          Format code (ruff format)"
	@echo ""
	@echo "  Benchmarks"
	@echo "    make bench        Run default benchmark suite"
	@echo ""

# ── Services ──────────────────────────────────────────────────────────────────

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

build:
	$(COMPOSE) build --no-cache

logs:
	$(COMPOSE) logs -f

logs-api:
	$(COMPOSE) logs -f api

# ── Dev (hot-reload) ──────────────────────────────────────────────────────────

dev-up:
	$(COMPOSE_DEV) up -d

dev-down:
	$(COMPOSE_DEV) down

dev-build:
	$(COMPOSE_DEV) build

dev-logs:
	$(COMPOSE_DEV) logs -f

# ── Database ──────────────────────────────────────────────────────────────────

migrate:
	$(COMPOSE) exec api alembic upgrade head

db-reset:
	$(COMPOSE) exec postgres psql -U inferx -c "DROP DATABASE IF EXISTS inferx;"
	$(COMPOSE) exec postgres psql -U inferx -c "CREATE DATABASE inferx;"
	$(MAKE) migrate

# ── Shells ────────────────────────────────────────────────────────────────────

shell-api:
	$(COMPOSE) exec api /bin/bash

shell-db:
	$(COMPOSE) exec postgres psql -U inferx -d inferx

# ── Quality ───────────────────────────────────────────────────────────────────

test:
	$(COMPOSE) exec api pytest tests/ -v

lint:
	$(COMPOSE) exec api ruff check apps/ packages/

fmt:
	$(COMPOSE) exec api ruff format apps/ packages/

# ── Benchmarks ────────────────────────────────────────────────────────────────

bench:
	$(COMPOSE) exec api python -m packages.benchmarks.runner --suite configs/benchmark_suites/default.yaml
