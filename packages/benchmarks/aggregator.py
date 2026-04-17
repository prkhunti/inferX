"""Stats aggregation over a list of per-request results."""

from __future__ import annotations

import statistics
from dataclasses import dataclass

from packages.schemas.model_profile import model_registry


@dataclass
class RequestResult:
    """Metrics captured for a single benchmark request."""

    success: bool
    ttft_ms: float = 0.0
    total_latency_ms: float = 0.0
    tokens_per_sec: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    error: str | None = None


@dataclass
class CaseStats:
    """Aggregated statistics for one benchmark case (grid cell)."""

    case_name: str
    model: str
    concurrency: int
    prompt_length: int
    output_length: int
    streaming: bool
    total_requests: int
    successful_requests: int
    error_rate: float

    # Latency percentiles (ms)
    p25_latency_ms: float
    p50_latency_ms: float
    p75_latency_ms: float
    p90_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float

    # TTFT (ms) — meaningful for streaming; equals ~total for sync
    avg_ttft_ms: float
    p50_ttft_ms: float
    p95_ttft_ms: float
    p99_ttft_ms: float

    # Throughput
    throughput_rps: float   # successful requests / wall-clock seconds
    throughput_tps: float   # total output tokens / wall-clock seconds

    wall_time_sec: float

    # Cost estimates (USD)
    avg_cost_per_request: float = 0.0    # based on actual token counts
    total_cost: float = 0.0
    cost_per_1k_output_tokens: float = 0.0


def _percentile(data: list[float], p: float) -> float:
    """Return the interpolated percentile value for a numeric series."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = (p / 100) * (len(sorted_data) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(sorted_data) - 1)
    frac = idx - lo
    return round(sorted_data[lo] + frac * (sorted_data[hi] - sorted_data[lo]), 2)


def _estimate_costs(
    model: str,
    results: list[RequestResult],
) -> tuple[float, float, float]:
    """Estimate aggregate benchmark costs.

    Parameters
    ----------
    model : str
        Registry key used to look up pricing metadata.
    results : list[RequestResult]
        Per-request benchmark results for a single case.

    Returns
    -------
    tuple[float, float, float]
        Average cost per request, total cost, and cost per 1k output tokens.
    """
    profile = model_registry.get(model)
    if not profile:
        return 0.0, 0.0, 0.0

    successful = [r for r in results if r.success]
    if not successful:
        return 0.0, 0.0, 0.0

    per_request = [
        profile.estimate_cost(r.prompt_tokens, r.completion_tokens)
        for r in successful
    ]
    total = round(sum(per_request), 8)
    avg = round(total / len(per_request), 8)

    total_output = sum(r.completion_tokens for r in successful)
    cost_per_1k = (
        round((total / total_output) * 1000, 6) if total_output > 0 else 0.0
    )

    return avg, total, cost_per_1k


def aggregate(
    case_name: str,
    model: str,
    concurrency: int,
    prompt_length: int,
    output_length: int,
    streaming: bool,
    results: list[RequestResult],
    wall_time_sec: float,
) -> CaseStats:
    """Aggregate raw request results into case-level benchmark statistics.

    Parameters
    ----------
    case_name : str
        Human-readable case identifier.
    model : str
        Registry key for the model under test.
    concurrency : int
        Number of in-flight requests allowed for the case.
    prompt_length : int
        Prompt size in tokens for the synthetic prompt.
    output_length : int
        Requested output length in tokens.
    streaming : bool
        Whether the case uses streaming generation.
    results : list[RequestResult]
        Raw results collected for the case.
    wall_time_sec : float
        End-to-end elapsed wall clock time for the case.

    Returns
    -------
    CaseStats
        Aggregated latency, throughput, and cost statistics.
    """
    successful = [r for r in results if r.success]
    failed = len(results) - len(successful)

    latencies = [r.total_latency_ms for r in successful]
    ttfts = [r.ttft_ms for r in successful]
    total_output_tokens = sum(r.completion_tokens for r in successful)

    error_rate = round(failed / len(results) if results else 1.0, 4)
    throughput_rps = round(len(successful) / wall_time_sec if wall_time_sec > 0 else 0.0, 3)
    throughput_tps = round(total_output_tokens / wall_time_sec if wall_time_sec > 0 else 0.0, 3)

    avg_cost, total_cost, cost_per_1k = _estimate_costs(model, results)

    return CaseStats(
        case_name=case_name,
        model=model,
        concurrency=concurrency,
        prompt_length=prompt_length,
        output_length=output_length,
        streaming=streaming,
        total_requests=len(results),
        successful_requests=len(successful),
        error_rate=error_rate,
        p25_latency_ms=_percentile(latencies, 25),
        p50_latency_ms=_percentile(latencies, 50),
        p75_latency_ms=_percentile(latencies, 75),
        p90_latency_ms=_percentile(latencies, 90),
        p95_latency_ms=_percentile(latencies, 95),
        p99_latency_ms=_percentile(latencies, 99),
        avg_latency_ms=round(statistics.mean(latencies), 2) if latencies else 0.0,
        min_latency_ms=round(min(latencies), 2) if latencies else 0.0,
        max_latency_ms=round(max(latencies), 2) if latencies else 0.0,
        avg_ttft_ms=round(statistics.mean(ttfts), 2) if ttfts else 0.0,
        p50_ttft_ms=_percentile(ttfts, 50),
        p95_ttft_ms=_percentile(ttfts, 95),
        p99_ttft_ms=_percentile(ttfts, 99),
        throughput_rps=throughput_rps,
        throughput_tps=throughput_tps,
        wall_time_sec=round(wall_time_sec, 3),
        avg_cost_per_request=avg_cost,
        total_cost=total_cost,
        cost_per_1k_output_tokens=cost_per_1k,
    )
