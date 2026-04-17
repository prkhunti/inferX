.PHONY: help up down build logs logs-api shell-api shell-db migrate db-reset test test-unit \
        test-integration test-eval lint format typecheck bench dev-up dev-down dev-build dev-logs

COMPOSE     = docker compose -f infra/docker-compose.yaml
COMPOSE_DEV = docker compose -f infra/docker-compose.yaml -f infra/docker-compose.dev.yaml

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-26s\033[0m %s\n", $$1, $$2}' | sort

# ── Services ──────────────────────────────────────────────────────────────────

up: ## Start all services
	$(COMPOSE) up -d

down: ## Stop all services
	$(COMPOSE) down

build: ## Rebuild all Docker images without cache
	$(COMPOSE) build --no-cache

logs: ## Tail logs from all services
	$(COMPOSE) logs -f

logs-api: ## Tail API logs only
	$(COMPOSE) logs -f api

# ── Dev (hot-reload) ──────────────────────────────────────────────────────────

dev-up: ## Start all services with hot reload
	$(COMPOSE_DEV) up -d

dev-down: ## Stop development services
	$(COMPOSE_DEV) down

dev-build: ## Build development images
	$(COMPOSE_DEV) build

dev-logs: ## Tail development service logs
	$(COMPOSE_DEV) logs -f

# ── Database ──────────────────────────────────────────────────────────────────

migrate: ## Run database migrations
	$(COMPOSE) exec api alembic upgrade head

db-reset: ## Drop and recreate the database
	$(COMPOSE) exec postgres psql -U inferx -c "DROP DATABASE IF EXISTS inferx;"
	$(COMPOSE) exec postgres psql -U inferx -c "CREATE DATABASE inferx;"
	$(MAKE) migrate

# ── Shells ────────────────────────────────────────────────────────────────────

shell-api: ## Open a shell in the API container
	$(COMPOSE) exec api /bin/bash

shell-db: ## Open psql in the Postgres container
	$(COMPOSE) exec postgres psql -U inferx -d inferx

# ── Quality ───────────────────────────────────────────────────────────────────

test: ## Run the full test suite
	$(COMPOSE) exec api pytest tests/ -v

test-unit: ## Run unit tests
	$(COMPOSE) exec api pytest tests/unit -v

test-integration: ## Run integration tests
	$(COMPOSE) exec api pytest tests/integration -v

test-eval: ## Run evaluation tests
	$(COMPOSE) exec api pytest tests/eval -v

lint: ## Run Ruff lint checks
	$(COMPOSE) exec api ruff check apps/ packages/

format: ## Format Python code with Ruff
	$(COMPOSE) exec api ruff format apps/ packages/

typecheck: ## Run mypy
	$(COMPOSE) exec api mypy apps packages tests

# ── Benchmarks ────────────────────────────────────────────────────────────────

bench: ## Run the default benchmark suite
	$(COMPOSE) exec api python -m packages.benchmarks.runner --suite configs/benchmark_suites/default.yaml
