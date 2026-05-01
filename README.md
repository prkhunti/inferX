# InferX

InferX is a portfolio/reference implementation of an LLM inference and benchmarking platform for comparing latency, throughput, streaming behavior, and estimated cost across model-serving configurations.

## Overview

InferX provides a FastAPI inference API, an async benchmark runner, persistent request/run metrics, Prometheus instrumentation, and a Next.js dashboard for exploring benchmark results. The default `echo` backend runs locally without external credentials, while the OpenAI-compatible backend can point at OpenAI or another compatible `/v1` endpoint.

This repository is intended to be read and evaluated as an engineering portfolio project. It is not currently accepting external contributions.

## Problem It Solves

LLM serving decisions often involve tradeoffs between first-token latency, total latency, throughput, concurrency, output length, model choice, and cost. InferX gives those tradeoffs a concrete test harness:

- Run repeatable benchmark suites from YAML configs.
- Compare synchronous and streaming generation paths.
- Capture request lifecycle metrics such as queue time, time to first token, and total latency.
- Review aggregate percentile results and per-request traces in a dashboard.
- Swap between a local simulated backend and OpenAI-compatible providers.

## Key Features

- Unified `/generate` and `/stream` API routes.
- Local `echo` backend for setup, CI, and demos without secrets.
- OpenAI-compatible backend with optional custom base URL.
- YAML benchmark suites with cross-product case expansion.
- Async benchmark execution with concurrency controls.
- P50/P95/P99 and throughput aggregation.
- Request persistence with SQLAlchemy async and Alembic migrations.
- Prometheus `/metrics` endpoint.
- Next.js dashboard for playground, benchmark runs, request traces, and comparisons.
- Docker Compose setup for API, dashboard, PostgreSQL, Redis, and Prometheus.

## Architecture

```text
Client / Dashboard
        |
        | HTTP / SSE
        v
FastAPI API
  - request timing middleware
  - inference routes
  - benchmark routes
  - Prometheus metrics
        |
        +--------------------+
        |                    |
        v                    v
Serving backend        Benchmark runner
  - echo               - YAML suite loading
  - OpenAI-compatible  - async concurrency
                       - percentile aggregation
        |                    |
        +---------+----------+
                  v
PostgreSQL + SQLAlchemy async + Alembic
```

### Main Components

| Path | Responsibility |
| --- | --- |
| `apps/api` | FastAPI app, routers, settings, DB wiring, middleware, metrics |
| `apps/dashboard` | Next.js dashboard and API client |
| `packages/serving` | Backend abstraction plus echo and OpenAI-compatible implementations |
| `packages/benchmarks` | Suite loading, case expansion, runner, aggregation |
| `packages/scheduler` | Request lifecycle timing |
| `packages/metrics` | Metrics persistence helpers |
| `packages/schemas` | Shared Pydantic request/response/model profile schemas |
| `configs/benchmark_suites` | YAML benchmark definitions |
| `configs/model_profiles` | Model metadata used for labels and cost estimates |
| `infra` | Dockerfiles, Compose files, Prometheus config |
| `tests` | Unit, integration, and placeholder evaluation tests |

## Tech Stack

| Area | Stack |
| --- | --- |
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy async, Alembic |
| Frontend | Next.js 14 App Router, React, TypeScript, Tailwind CSS, Recharts |
| Serving | Local echo backend, OpenAI Python SDK for OpenAI-compatible APIs |
| Data | PostgreSQL, Redis |
| Observability | Prometheus instrumentation, structured JSON logging |
| Tooling | Docker Compose, pytest, Ruff, mypy |

## Screenshots And Demo

Screenshots and demo media are not included yet.

TODO:

- Add dashboard screenshots for Playground, Benchmarks, Requests, and Compare.
- Add a short demo GIF showing a local benchmark run.
- Add a rendered architecture diagram under `docs/architecture/`.

## Local Setup

### Prerequisites

- Docker and Docker Compose
- `make`
- Optional: an API key for OpenAI or another OpenAI-compatible provider

The default configuration uses `BACKEND_TYPE=echo`, which requires no external credentials.

### Start With Docker Compose

```bash
cp .env.example .env
make build
make up
make migrate
```

Open:

| Service | URL |
| --- | --- |
| Dashboard | http://localhost:3000 |
| API docs | http://localhost:8000/docs |
| API health | http://localhost:8000/health |
| Prometheus | http://localhost:9090 |

Stop services:

```bash
make down
```

### Development Mode

Use the dev Compose overlay for API reloads and Next.js hot module replacement.

```bash
make dev-build
make dev-up
make migrate
```

Tail logs:

```bash
make dev-logs
```

## Environment Variables

Copy `.env.example` to `.env` for local use.

| Variable | Required | Description |
| --- | --- | --- |
| `BACKEND_TYPE` | Yes | `echo` for local simulated responses, or `openai` for the OpenAI-compatible backend. |
| `OPENAI_API_KEY` | Only with `BACKEND_TYPE=openai` | API key for the selected provider. Use a placeholder or omit it when using `echo`. |
| `OPENAI_BASE_URL` | No | Optional OpenAI-compatible base URL, such as a local vLLM server or provider endpoint. |
| `DATABASE_URL` | Yes for local Python API runs | SQLAlchemy async database URL. Compose injects its own container-to-container URL. |
| `REDIS_URL` | Yes for local Python API runs | Redis connection URL. Compose injects its own container-to-container URL. |
| `DEBUG` | No | Enables debug logging when set to `true`. |
| `NEXT_PUBLIC_API_URL` | No | API URL used by the dashboard rewrite proxy. Defaults to `http://localhost:8000` outside Docker. |

## Common Commands

```bash
make help              # list available Make targets
make up                # start services
make down              # stop services
make logs              # tail all service logs
make logs-api          # tail API logs
make migrate           # apply Alembic migrations
make test              # run pytest in the API container
make test-unit         # run unit tests
make test-integration  # run integration tests
make lint              # run Ruff
make format            # format Python code with Ruff
make typecheck         # run mypy
```

## Running A Benchmark

From the dashboard, open **Benchmarks**, select a suite, and start a run.

From the API:

```bash
curl -X POST http://localhost:8000/benchmarks/run \
  -H "Content-Type: application/json" \
  -d '{"suite_file": "concurrency_scaling.yaml"}'
```

Then poll the returned run ID:

```bash
curl http://localhost:8000/benchmarks/{run_id}
curl http://localhost:8000/benchmarks/{run_id}/results
```

Compare completed runs:

```bash
curl "http://localhost:8000/benchmarks/compare?ids={run_id_1},{run_id_2}"
```

## Benchmark Suites

Prebuilt suites live in `configs/benchmark_suites/`.

| Suite | Focus |
| --- | --- |
| `default.yaml` | Baseline local benchmark |
| `concurrency_scaling.yaml` | Tail latency and throughput under higher concurrency |
| `streaming_vs_sync.yaml` | Streaming versus non-streaming behavior |
| `prompt_length_sensitivity.yaml` | Prompt length impact |
| `output_length_sensitivity.yaml` | Output length impact |
| `model_comparison.yaml` | Model-to-model comparison |
| `batching_tradeoff.yaml` | Concurrency tradeoffs relevant to batching decisions |

Example suite:

```yaml
name: concurrency_scaling
model: gpt-4o-mini
concurrency_levels: [1, 5, 10, 25, 50]
prompt_lengths: [200]
output_lengths: [150]
streaming: [false]
runs_per_case: 10
temperature: 0.0
```

## Using A Real Backend

Set the backend to `openai` and provide credentials in `.env`:

```bash
BACKEND_TYPE=openai
OPENAI_API_KEY=replace-with-provider-key
```

For another OpenAI-compatible endpoint, also set:

```bash
OPENAI_BASE_URL=http://localhost:8001/v1
```

Update benchmark suite `model` values to match the target provider.

## Testing

The Docker path is the primary supported test path:

```bash
make test
```

The test suite includes unit tests for benchmark/scheduler logic and integration tests for API routes. Tests use safe local defaults and do not require a real model provider.

## Repository Status And Limitations

- Portfolio/reference implementation, not a production deployment.
- No production hosting, SLO, uptime, or usage claims are made by this repository.
- Screenshots and demo media still need to be supplied.
- The `echo` backend is for local development and deterministic setup, not model-quality evaluation.
- Real-provider benchmark results depend on the selected endpoint, model, rate limits, and network conditions.
- Redis is included in the local stack, but the current code path primarily uses PostgreSQL for persisted request and benchmark data.

## Portfolio Note

InferX is published to demonstrate API design, async Python service design, benchmark orchestration, frontend observability workflows, Docker-based local setup, and practical LLM-serving measurement patterns.

This repository is not currently accepting external issues or pull requests. You may read, clone, and use the project subject to the license.

## Maintainer

Maintained by Prakash Khunti.

TODO: Add preferred portfolio, GitHub, LinkedIn, or email contact before publishing.
