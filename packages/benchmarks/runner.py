"""Async benchmark runner.

Execution model
---------------
For each BenchmarkCase the runner sends `runs_per_case` requests with
`concurrency` in-flight at a time, controlled by an asyncio.Semaphore.
All requests within a case are launched together via asyncio.gather so
wall-clock time reflects true concurrent load.

Streaming requests collect the full token stream and report TTFT from the
first received chunk; sync requests report TTFT == total latency (no
observable first-token moment).
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from packages.benchmarks.aggregator import CaseStats, RequestResult, aggregate
from packages.benchmarks.suite import BenchmarkCase, BenchmarkSuiteConfig, expand_suite, synthetic_prompt
from packages.serving.base import BaseBackend

logger = logging.getLogger(__name__)


# ── Run state ─────────────────────────────────────────────────────────────

@dataclass
class BenchmarkRun:
    id: str = field(default_factory=lambda: str(uuid4()))
    suite_name: str = ""
    status: str = "pending"          # pending | running | completed | failed
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    case_stats: list[CaseStats] = field(default_factory=list)
    error: Optional[str] = None

    def total_cases(self) -> int:
        return len(self.case_stats)


# ── Single-request execution ───────────────────────────────────────────────

async def _run_single(
    case: BenchmarkCase,
    backend: BaseBackend,
    semaphore: asyncio.Semaphore,
) -> RequestResult:
    prompt = synthetic_prompt(case.prompt_length)

    async with semaphore:
        start = time.perf_counter()
        ttft_mark: Optional[float] = None

        try:
            if case.streaming:
                completion_tokens = 0
                async for chunk in backend.stream(
                    prompt=prompt,
                    model=case.model,
                    temperature=case.temperature,
                    max_tokens=case.output_length,
                ):
                    if chunk.is_final:
                        completion_tokens = chunk.completion_tokens or 0
                        break
                    if ttft_mark is None:
                        ttft_mark = time.perf_counter()

                end = time.perf_counter()
                ttft_ms = ((ttft_mark or end) - start) * 1000
                total_ms = (end - start) * 1000
                gen_sec = (end - (ttft_mark or end))
                tps = completion_tokens / gen_sec if gen_sec > 0 else 0.0

                return RequestResult(
                    success=True,
                    ttft_ms=round(ttft_ms, 2),
                    total_latency_ms=round(total_ms, 2),
                    tokens_per_sec=round(tps, 2),
                    completion_tokens=completion_tokens,
                )

            else:
                result = await backend.generate(
                    prompt=prompt,
                    model=case.model,
                    temperature=case.temperature,
                    max_tokens=case.output_length,
                )
                end = time.perf_counter()
                total_ms = (end - start) * 1000
                gen_sec = end - start
                tps = result.completion_tokens / gen_sec if gen_sec > 0 else 0.0

                return RequestResult(
                    success=True,
                    ttft_ms=round(total_ms, 2),   # no observable TTFT for sync
                    total_latency_ms=round(total_ms, 2),
                    tokens_per_sec=round(tps, 2),
                    prompt_tokens=result.prompt_tokens,
                    completion_tokens=result.completion_tokens,
                )

        except Exception as exc:
            end = time.perf_counter()
            logger.warning(
                "benchmark.request_failed case=%s error=%s",
                case.name,
                exc,
            )
            return RequestResult(
                success=False,
                total_latency_ms=round((end - start) * 1000, 2),
                error=str(exc),
            )


# ── Case runner ────────────────────────────────────────────────────────────

async def _run_case(case: BenchmarkCase, backend: BaseBackend) -> CaseStats:
    logger.info(
        "benchmark.case_start case=%s concurrency=%d runs=%d",
        case.name,
        case.concurrency,
        case.runs_per_case,
    )

    semaphore = asyncio.Semaphore(case.concurrency)
    tasks = [
        _run_single(case, backend, semaphore)
        for _ in range(case.runs_per_case)
    ]

    wall_start = time.perf_counter()
    results = await asyncio.gather(*tasks)
    wall_time = time.perf_counter() - wall_start

    stats = aggregate(
        case_name=case.name,
        model=case.model,
        concurrency=case.concurrency,
        prompt_length=case.prompt_length,
        output_length=case.output_length,
        streaming=case.streaming,
        results=list(results),
        wall_time_sec=wall_time,
    )

    logger.info(
        "benchmark.case_done case=%s p50=%.1fms p95=%.1fms rps=%.2f err=%.1f%%",
        case.name,
        stats.p50_latency_ms,
        stats.p95_latency_ms,
        stats.throughput_rps,
        stats.error_rate * 100,
    )

    return stats


# ── Suite runner ───────────────────────────────────────────────────────────

async def run_suite(
    cfg: BenchmarkSuiteConfig,
    backend: BaseBackend,
    run: BenchmarkRun,
) -> None:
    """Execute all cases in `cfg` sequentially and populate `run` in-place.

    Cases are run sequentially (not concurrently) so results are comparable
    and the model backend isn't saturated by multiple experiments at once.
    Concurrency within each case is controlled by BenchmarkCase.concurrency.
    """
    run.status = "running"
    run.started_at = datetime.now(timezone.utc)
    cases = expand_suite(cfg)

    logger.info(
        "benchmark.suite_start suite=%s total_cases=%d",
        cfg.name,
        len(cases),
    )

    try:
        for case in cases:
            stats = await _run_case(case, backend)
            run.case_stats.append(stats)

        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        logger.info(
            "benchmark.suite_done suite=%s cases=%d",
            cfg.name,
            len(run.case_stats),
        )

    except Exception as exc:
        run.status = "failed"
        run.completed_at = datetime.now(timezone.utc)
        run.error = str(exc)
        logger.exception("benchmark.suite_failed suite=%s", cfg.name)
