import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from apps.api.dependencies import get_backend
from apps.api.store import benchmark_store
from packages.benchmarks.runner import BenchmarkRun, run_suite
from packages.benchmarks.suite import BenchmarkSuiteConfig
from packages.serving.openai_backend import OpenAIBackend

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Request / Response models ──────────────────────────────────────────────

class RunRequest(BaseModel):
    """Inline suite definition or path to a YAML config file."""

    suite: Optional[BenchmarkSuiteConfig] = Field(
        default=None,
        description="Inline suite definition",
    )
    suite_file: Optional[str] = Field(
        default=None,
        description="Path to a YAML suite file inside configs/benchmark_suites/",
    )

    model_config = {"json_schema_extra": {"example": {
        "suite": {
            "name": "quick_smoke",
            "model": "gpt-4o-mini",
            "concurrency_levels": [1, 5],
            "prompt_lengths": [100],
            "output_lengths": [100],
            "streaming": [False],
            "runs_per_case": 3,
        }
    }}}


class RunSummary(BaseModel):
    id: str
    suite_name: str
    status: str
    started_at: Optional[str]
    completed_at: Optional[str]
    total_cases: int
    error: Optional[str]


class CaseStatsResponse(BaseModel):
    case_name: str
    model: str
    concurrency: int
    prompt_length: int
    output_length: int
    streaming: bool
    total_requests: int
    successful_requests: int
    error_rate: float
    # Full latency distribution
    min_latency_ms: float
    p25_latency_ms: float
    p50_latency_ms: float
    p75_latency_ms: float
    p90_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    max_latency_ms: float
    avg_latency_ms: float
    # TTFT distribution
    avg_ttft_ms: float
    p50_ttft_ms: float
    p95_ttft_ms: float
    p99_ttft_ms: float
    # Throughput + cost
    throughput_rps: float
    throughput_tps: float
    wall_time_sec: float
    avg_cost_per_request: float
    total_cost: float
    cost_per_1k_output_tokens: float


class RunResultsResponse(BaseModel):
    id: str
    suite_name: str
    status: str
    started_at: Optional[str]
    completed_at: Optional[str]
    cases: list[CaseStatsResponse]


class CompareRunEntry(BaseModel):
    """One run's summary + cases, used in comparison responses."""
    id: str
    suite_name: str
    model: str                     # primary model across cases (first case's model)
    started_at: Optional[str]
    cases: list[CaseStatsResponse]


class CompareResponse(BaseModel):
    runs: list[CompareRunEntry]


# ── Helpers ────────────────────────────────────────────────────────────────

def _to_summary(run: BenchmarkRun) -> RunSummary:
    return RunSummary(
        id=run.id,
        suite_name=run.suite_name,
        status=run.status,
        started_at=run.started_at.isoformat() if run.started_at else None,
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        total_cases=run.total_cases(),
        error=run.error,
    )


def _to_results(run: BenchmarkRun) -> RunResultsResponse:
    return RunResultsResponse(
        id=run.id,
        suite_name=run.suite_name,
        status=run.status,
        started_at=run.started_at.isoformat() if run.started_at else None,
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        cases=[CaseStatsResponse(**cs.__dict__) for cs in run.case_stats],
    )


def _load_suite(req: RunRequest) -> BenchmarkSuiteConfig:
    if req.suite:
        return req.suite
    if req.suite_file:
        path = f"configs/benchmark_suites/{req.suite_file}"
        try:
            return BenchmarkSuiteConfig.from_yaml(path)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Suite file not found: {path}")
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Invalid suite file: {exc}")
    raise HTTPException(
        status_code=422,
        detail="Provide either 'suite' (inline) or 'suite_file' (YAML path).",
    )


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.post("/run", response_model=RunSummary, status_code=202, summary="Start a benchmark run")
async def start_run(
    req: RunRequest,
    background_tasks: BackgroundTasks,
    backend: OpenAIBackend = Depends(get_backend),
) -> RunSummary:
    """
    Launch a benchmark suite as a background task and return immediately
    with the run ID. Poll `GET /benchmarks/{id}` to track status, then
    fetch `GET /benchmarks/{id}/results` when status is `completed`.
    """
    cfg = _load_suite(req)

    run = BenchmarkRun(suite_name=cfg.name, status="pending")
    benchmark_store.save(run)

    logger.info(
        "benchmark.run_accepted run_id=%s suite=%s",
        run.id,
        cfg.name,
    )

    background_tasks.add_task(run_suite, cfg, backend, run)

    return _to_summary(run)


@router.get("", response_model=list[RunSummary], summary="List all benchmark runs")
async def list_runs() -> list[RunSummary]:
    return [_to_summary(r) for r in benchmark_store.list_all()]


@router.get("/compare", response_model=CompareResponse, summary="Compare multiple completed runs")
async def compare_runs(ids: str) -> CompareResponse:
    """
    Fetch and align results from two or more completed runs for side-by-side comparison.

    Pass a comma-separated list of run IDs: `?ids=id1,id2,id3`

    Only completed runs are included; pending/running/failed runs are skipped
    with a warning rather than returning an error, so a partial comparison is
    still usable.
    """
    run_ids = [r.strip() for r in ids.split(",") if r.strip()]
    if len(run_ids) < 2:
        raise HTTPException(status_code=422, detail="Provide at least two run IDs.")

    entries: list[CompareRunEntry] = []
    for run_id in run_ids:
        run = benchmark_store.get(run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"Run {run_id!r} not found")
        if run.status != "completed":
            logger.warning("compare.skip run_id=%s status=%s", run_id, run.status)
            continue

        primary_model = run.case_stats[0].model if run.case_stats else "unknown"
        entries.append(CompareRunEntry(
            id=run.id,
            suite_name=run.suite_name,
            model=primary_model,
            started_at=run.started_at.isoformat() if run.started_at else None,
            cases=[CaseStatsResponse(**cs.__dict__) for cs in run.case_stats],
        ))

    if not entries:
        raise HTTPException(status_code=422, detail="No completed runs found among provided IDs.")

    return CompareResponse(runs=entries)


@router.get("/{run_id}", response_model=RunSummary, summary="Get run status")
async def get_run(run_id: str) -> RunSummary:
    run = benchmark_store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id!r} not found")
    return _to_summary(run)


@router.get("/{run_id}/results", response_model=RunResultsResponse, summary="Get full results")
async def get_results(run_id: str) -> RunResultsResponse:
    run = benchmark_store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id!r} not found")
    if run.status == "pending":
        raise HTTPException(status_code=202, detail="Run has not started yet")
    if run.status == "running":
        raise HTTPException(status_code=202, detail="Run is still in progress")
    return _to_results(run)
