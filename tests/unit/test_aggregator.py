"""Unit tests for packages/benchmarks/aggregator.py."""

import pytest

from packages.benchmarks.aggregator import RequestResult, _percentile, aggregate

# ── _percentile ────────────────────────────────────────────────────────────────

class TestPercentile:
    def test_empty_returns_zero(self):
        assert _percentile([], 50) == 0.0

    def test_single_value(self):
        assert _percentile([42.0], 50) == 42.0
        assert _percentile([42.0], 99) == 42.0

    def test_known_percentiles(self):
        data = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
        assert _percentile(data, 50) == 55.0   # midpoint interpolation
        assert _percentile(data, 0) == 10.0
        assert _percentile(data, 100) == 100.0

    def test_unsorted_input(self):
        data = [100.0, 10.0, 50.0]
        # sorted: [10, 50, 100] → p50 = 50
        assert _percentile(data, 50) == 50.0

    def test_p95_greater_than_p50(self):
        data = list(range(1, 101, 1))
        data_f = [float(x) for x in data]
        assert _percentile(data_f, 95) > _percentile(data_f, 50)

    def test_monotonically_increasing(self):
        data = [float(x) for x in range(1, 21)]
        p25 = _percentile(data, 25)
        p50 = _percentile(data, 50)
        p75 = _percentile(data, 75)
        p95 = _percentile(data, 95)
        assert p25 < p50 < p75 < p95


# ── aggregate ──────────────────────────────────────────────────────────────────

def make_results(latencies: list[float], ttfts: list[float] | None = None) -> list[RequestResult]:
    """Helper: build successful RequestResult list from latency values."""
    ttfts = ttfts or latencies
    return [
        RequestResult(
            success=True,
            total_latency_ms=lat,
            ttft_ms=ttft,
            tokens_per_sec=10.0,
            prompt_tokens=100,
            completion_tokens=50,
        )
        for lat, ttft in zip(latencies, ttfts)
    ]


class TestAggregate:
    def test_basic_structure(self):
        results = make_results([100.0, 200.0, 300.0])
        stats = aggregate(
            case_name="test_case",
            model="gpt-4o-mini",
            concurrency=1,
            prompt_length=100,
            output_length=50,
            streaming=False,
            results=results,
            wall_time_sec=1.0,
        )
        assert stats.case_name == "test_case"
        assert stats.model == "gpt-4o-mini"
        assert stats.total_requests == 3
        assert stats.successful_requests == 3
        assert stats.error_rate == 0.0

    def test_latency_ordering(self):
        results = make_results([100.0, 200.0, 300.0, 400.0, 500.0])
        stats = aggregate("c", "m", 1, 100, 50, False, results, 1.0)
        assert stats.p50_latency_ms <= stats.p95_latency_ms
        assert stats.p50_latency_ms <= stats.p99_latency_ms
        assert stats.min_latency_ms <= stats.p50_latency_ms
        assert stats.p99_latency_ms <= stats.max_latency_ms

    def test_min_max(self):
        results = make_results([50.0, 150.0, 250.0])
        stats = aggregate("c", "m", 1, 100, 50, False, results, 1.0)
        assert stats.min_latency_ms == 50.0
        assert stats.max_latency_ms == 250.0

    def test_avg_latency(self):
        results = make_results([100.0, 200.0, 300.0])
        stats = aggregate("c", "m", 1, 100, 50, False, results, 1.0)
        assert stats.avg_latency_ms == pytest.approx(200.0, abs=0.1)

    def test_throughput_rps(self):
        results = make_results([100.0] * 10)
        stats = aggregate("c", "m", 1, 100, 50, False, results, 2.0)
        # 10 successful requests / 2 seconds = 5 rps
        assert stats.throughput_rps == pytest.approx(5.0, abs=0.01)

    def test_throughput_tps(self):
        # Each result has 50 completion_tokens, 10 results, 2 sec wall time
        results = make_results([100.0] * 10)
        stats = aggregate("c", "m", 1, 100, 50, False, results, 2.0)
        # 10 * 50 tokens / 2 sec = 250 tps
        assert stats.throughput_tps == pytest.approx(250.0, abs=0.1)

    def test_error_rate(self):
        good = make_results([100.0] * 8)
        bad = [RequestResult(success=False, total_latency_ms=50.0, error="timeout")]
        bad2 = [RequestResult(success=False, total_latency_ms=60.0, error="timeout")]
        results = good + bad + bad2
        stats = aggregate("c", "m", 1, 100, 50, False, results, 1.0)
        assert stats.total_requests == 10
        assert stats.successful_requests == 8
        assert stats.error_rate == pytest.approx(0.2, abs=0.001)

    def test_all_failures(self):
        results = [RequestResult(success=False, total_latency_ms=50.0, error="err")]
        stats = aggregate("c", "m", 1, 100, 50, False, results, 1.0)
        assert stats.error_rate == 1.0
        assert stats.successful_requests == 0
        assert stats.p50_latency_ms == 0.0
        assert stats.throughput_rps == 0.0

    def test_empty_results(self):
        stats = aggregate("c", "m", 1, 100, 50, False, [], 1.0)
        assert stats.error_rate == 1.0
        assert stats.total_requests == 0

    def test_cost_zero_without_model_profile(self):
        """Model not in registry → costs fall back to 0."""
        results = make_results([100.0] * 5)
        stats = aggregate("c", "unknown-model-xyz", 1, 100, 50, False, results, 1.0)
        assert stats.avg_cost_per_request == 0.0
        assert stats.total_cost == 0.0

    def test_ttft_stats(self):
        ttfts = [10.0, 20.0, 30.0, 40.0, 50.0]
        results = make_results([100.0] * 5, ttfts=ttfts)
        stats = aggregate("c", "m", 1, 100, 50, True, results, 1.0)
        assert stats.avg_ttft_ms == pytest.approx(30.0, abs=0.1)
        assert stats.p50_ttft_ms <= stats.p95_ttft_ms
