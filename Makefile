.PHONY: help up down build logs shell-api shell-db migrate test lint fmt

COMPOSE = docker compose -f infra/docker-compose.yml

# Default target
help:
	@echo ""
	@echo "InferX — available commands:"
	@echo ""
	@echo "  Dev"
	@echo "    make up           Start all services"
	@echo "    make down         Stop all services"
	@echo "    make build        Rebuild all Docker images"
	@echo "    make logs         Tail logs from all services"
	@echo "    make logs-api     Tail API logs only"
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
