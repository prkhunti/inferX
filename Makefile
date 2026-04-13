.PHONY: help up down build logs shell-api shell-db migrate test lint fmt

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
	docker compose up -d

down:
	docker compose down

build:
	docker compose build --no-cache

logs:
	docker compose logs -f

logs-api:
	docker compose logs -f api

# ── Database ──────────────────────────────────────────────────────────────────

migrate:
	docker compose exec api alembic upgrade head

db-reset:
	docker compose exec postgres psql -U inferx -c "DROP DATABASE IF EXISTS inferx;"
	docker compose exec postgres psql -U inferx -c "CREATE DATABASE inferx;"
	$(MAKE) migrate

# ── Shells ────────────────────────────────────────────────────────────────────

shell-api:
	docker compose exec api /bin/bash

shell-db:
	docker compose exec postgres psql -U inferx -d inferx

# ── Quality ───────────────────────────────────────────────────────────────────

test:
	docker compose exec api pytest tests/ -v

lint:
	docker compose exec api ruff check apps/ packages/

fmt:
	docker compose exec api ruff format apps/ packages/

# ── Benchmarks ────────────────────────────────────────────────────────────────

bench:
	docker compose exec api python -m packages.benchmarks.runner --suite configs/benchmark_suites/default.yaml
