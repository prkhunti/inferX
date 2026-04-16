# InferX

**Low-Latency LLM Inference and Benchmarking Platform**

InferX is a production-style platform for serving large language models and measuring the latency, throughput, and cost tradeoffs across serving configurations. It exposes a unified inference API, an async benchmark runner, a Prometheus metrics endpoint, and an analytics dashboard — built to answer the questions that matter in production AI systems.

---

## What it measures

| Metric | Definition |
|---|---|
| **TTFT** | Time from request acceptance to first emitted token |
| **Total latency** | Time from request acceptance to final token |
| **Tokens/sec (TPS)** | Output tokens ÷ active generation time |
| **Requests/sec (RPS)** | Completed requests ÷ wall-clock time under load |
| **P50 / P95 / P99** | Latency percentiles under benchmark load |
| **Queue time** | Time the request waited before the backend started |
| **Cost / request** | Estimated cost using per-model token pricing |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Client / Dashboard                                         │
└─────────────────┬───────────────────────────────────────────┘
                  │  HTTP / SSE
┌─────────────────▼───────────────────────────────────────────┐
│  FastAPI  ·  RequestTimingMiddleware  ·  Prometheus          │
│                                                             │
│  POST /generate     POST /stream     POST /benchmarks/run   │
│  GET  /benchmarks   GET  /compare    GET  /models           │
│  GET  /requests     GET  /metrics                           │
└─────────┬───────────────────┬───────────────────────────────┘
          │                   │
┌─────────▼────────┐ ┌────────▼────────────────────────────────┐
│  OpenAI Backend  │ │  Benchmark Runner                        │
│  (pluggable —    │ │  asyncio.Semaphore concurrency control   │
│  vLLM, Groq,     │ │  cross-product case expansion            │
│  Together, etc.) │ │  P25/P50/P75/P90/P95/P99 aggregation    │
└─────────┬────────┘ └────────┬────────────────────────────────┘
          │                   │
┌─────────▼───────────────────▼───────────────────────────────┐
│  PostgreSQL  ·  SQLAlchemy async  ·  Alembic migrations     │
│  requests · request_metrics · benchmark_runs · cases        │
└─────────────────────────────────────────────────────────────┘
```

**Packages**

| Package | Responsibility |
|---|---|
| `packages/serving` | Abstract `BaseBackend` + OpenAI-compatible implementation |
| `packages/scheduler` | `RequestLifecycle` — enqueue / start / first-token / completion timing |
| `packages/benchmarks` | Suite definition, case expansion, async runner, percentile aggregator |
| `packages/metrics` | Fire-and-forget DB writes via `asyncio.create_task` |
| `packages/schemas` | Shared Pydantic models and `ModelProfile` / `ModelRegistry` |

---

## Dashboard

**Playground** — live inference with streaming toggle, real-time TTFT and latency display

**Benchmarks** — launch runs from YAML suite configs, poll status, inspect full percentile distributions and tail-latency curves

**Requests** — per-request trace: queue time, TTFT, total latency, token counts, cost estimate

**Compare** — select two or more completed runs for side-by-side comparison; configurable metric and group-by axis; star-highlighted best values in summary table

---

## Benchmark suites

Pre-built suites live in `configs/benchmark_suites/`. Each is a YAML cross-product of concurrency × prompt length × output length × streaming mode.

| Suite | Question |
|---|---|
| `prompt_length_sensitivity` | How does prompt length drive latency and throughput? |
| `concurrency_scaling` | Where does tail latency break under increasing load? |
| `streaming_vs_sync` | What is the TTFT and total-latency tradeoff for streaming? |
| `output_length_sensitivity` | How much does output length dominate latency vs prompt length? |
| `model_comparison` | Which model wins on cost-adjusted throughput for a given workload? |
| `batching_tradeoff` | How does concurrency change P95 latency vs RPS? |

**Suite format**

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

---

## Tech stack

**Backend** — Python 3.11, FastAPI, Pydantic v2, SQLAlchemy async (asyncpg), Alembic, Prometheus

**Frontend** — Next.js 14 App Router, TypeScript, Tailwind CSS, Recharts

**Infrastructure** — Docker Compose, PostgreSQL 16, Redis 7, Prometheus

---

## Local setup

**Prerequisites:** Docker and Docker Compose. An API key is optional — the default `echo` backend runs locally with no credentials and simulated latency.

```bash
# 1. Clone and configure
git clone https://github.com/your-username/inferX.git
cd inferX
cp .env.example .env
# BACKEND_TYPE=echo is the default — works out of the box with no API key.
# To use a real model: set BACKEND_TYPE=openai and OPENAI_API_KEY=sk-... in .env

# 2. Build and start all services
make build
make up

# 3. Run database migrations
make migrate

# 4. Open the dashboard
open http://localhost:3000

# API docs
open http://localhost:8000/docs
```

| Service | URL |
|---|---|
| Dashboard | http://localhost:3000 |
| API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| Prometheus | http://localhost:9090 |

**Useful commands**

```bash
make up            # start all services
make down          # stop all services
make logs          # tail all service logs
make logs-api      # tail API logs only
make shell-api     # bash inside API container
make shell-db      # psql inside postgres container
make migrate       # run pending Alembic migrations
make test          # run pytest
make lint          # ruff check
make fmt           # ruff format
```

---

## Development workflow

Use `make dev-up` instead of `make up` to get hot-reload on both the API and the dashboard.

```bash
make dev-build     # build dev images (only needed once, or after dependency changes)
make dev-up        # start all services with hot-reload
make dev-logs      # tail logs
make dev-down      # stop dev services
```

| What changes | How |
|---|---|
| **API** | `uvicorn --reload` — Python file saves restart the server automatically |
| **Dashboard** | `next dev` with source volume-mounted — edits trigger HMR in the browser instantly |
| **DB / Redis / Prometheus** | Same images as prod — no difference |

> **First run only:** `make dev-build` builds the lightweight dev dashboard image (`Dockerfile.dashboard.dev`) which installs `node_modules` inside the container. Subsequent `make dev-up` calls reuse the image and the named `dashboard_node_modules` volume.

---

## Running a benchmark

**Via dashboard** — open Benchmarks, select a suite file, click Run, watch status update, open results.

**Via API**

```bash
# Launch a suite defined inline
curl -X POST http://localhost:8000/benchmarks/run \
  -H "Content-Type: application/json" \
  -d '{"suite_file": "concurrency_scaling.yaml"}'

# Returns: {"id": "run-abc123", "status": "pending", ...}

# Poll until status == "completed"
curl http://localhost:8000/benchmarks/run-abc123

# Fetch full results
curl http://localhost:8000/benchmarks/run-abc123/results

# Compare two runs
curl "http://localhost:8000/benchmarks/compare?ids=run-abc123,run-def456"
```

---

## Pointing at a different backend

Set `OPENAI_BASE_URL` in `.env` to route to any OpenAI-compatible endpoint:

```bash
# Local vLLM
OPENAI_BASE_URL=http://localhost:8001/v1

# Together AI
OPENAI_BASE_URL=https://api.together.xyz/v1

# Groq
OPENAI_BASE_URL=https://api.groq.com/openai/v1
```

Update `model` in your suite YAML to match the target model ID. No code changes required.

---

## Key observability signals

The API emits structured JSON logs and a Prometheus `/metrics` endpoint on every request.

**Request log fields**

```json
{
  "request_id": "abc-123",
  "model": "gpt-4o-mini",
  "queue_ms": 1.2,
  "ttft_ms": 312.4,
  "total_latency_ms": 1840.7,
  "tokens_per_sec": 48.3,
  "prompt_tokens": 204,
  "output_tokens": 148,
  "cost_usd": 0.000062
}
```

**Prometheus metrics** — TTFT histogram, end-to-end latency histogram, tokens/sec histogram, request counter by model and status.

---

## Repo structure

```
inferx/
├── apps/
│   ├── api/                      # FastAPI app — routers, middleware, DB, metrics
│   └── dashboard/                # Next.js 14 dashboard
├── packages/
│   ├── serving/                  # Backend abstraction + OpenAI / Echo implementations
│   ├── scheduler/                # Request lifecycle timing
│   ├── benchmarks/               # Suite definition, runner, aggregator
│   ├── metrics/                  # Async metrics persistence
│   └── schemas/                  # Shared Pydantic models, ModelRegistry
├── configs/
│   ├── benchmark_suites/         # YAML experiment definitions
│   └── model_profiles/           # Per-model cost and capability metadata
├── infra/
│   ├── docker/                   # Dockerfiles, Prometheus config
│   │   ├── Dockerfile.api
│   │   ├── Dockerfile.dashboard       # Production (standalone Next.js build)
│   │   ├── Dockerfile.dashboard.dev   # Dev (npm run dev + volume mount)
│   │   └── prometheus.yml
│   ├── docker-compose.yml        # Production compose
│   └── docker-compose.dev.yml    # Development overrides (hot-reload)
├── .github/workflows/ci.yml      # CI — build + pytest in Docker
├── alembic/                      # DB migrations
└── tests/
    ├── unit/                     # Pure logic tests (aggregator, suite, tracker)
    └── integration/              # HTTP tests via ASGI transport
```

---

## Roadmap

- [ ] Dynamic batching — batch compatible concurrent requests before dispatch
- [ ] Multiple backend routing — route by model ID, latency SLO, or cost budget
- [ ] Quantized model comparison — measure quality-vs-speed tradeoff for GGUF/AWQ/GPTQ variants
- [ ] KV-cache simulation — model the effect of prompt-prefix caching on TTFT
- [ ] Kubernetes manifests — horizontal scaling simulation
- [ ] Grafana dashboards — pre-built panels for latency, throughput, and cost
