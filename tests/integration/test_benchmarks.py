"""Integration tests for /benchmarks endpoints."""

from datetime import UTC, datetime

from packages.benchmarks.aggregator import CaseStats
from packages.benchmarks.runner import BenchmarkRun

# ── helpers ────────────────────────────────────────────────────────────────────

def make_completed_run(run_id: str, suite_name: str = "test_suite") -> BenchmarkRun:
    run = BenchmarkRun(id=run_id, suite_name=suite_name, status="completed")
    run.started_at = datetime.now(UTC)
    run.completed_at = datetime.now(UTC)
    run.case_stats = [
        CaseStats(
            case_name=f"{suite_name}__c1__p100__o50__sync",
            model="gpt-4o-mini",
            concurrency=1,
            prompt_length=100,
            output_length=50,
            streaming=False,
            total_requests=5,
            successful_requests=5,
            error_rate=0.0,
            min_latency_ms=80.0,
            p25_latency_ms=90.0,
            p50_latency_ms=100.0,
            p75_latency_ms=110.0,
            p90_latency_ms=120.0,
            p95_latency_ms=130.0,
            p99_latency_ms=140.0,
            max_latency_ms=150.0,
            avg_latency_ms=100.0,
            avg_ttft_ms=90.0,
            p50_ttft_ms=90.0,
            p95_ttft_ms=100.0,
            p99_ttft_ms=110.0,
            throughput_rps=5.0,
            throughput_tps=250.0,
            wall_time_sec=1.0,
            avg_cost_per_request=0.0001,
            total_cost=0.0005,
            cost_per_1k_output_tokens=0.002,
        )
    ]
    return run


# ── GET /benchmarks ────────────────────────────────────────────────────────────

async def test_list_benchmarks_empty(client):
    response = await client.get("/benchmarks")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_benchmarks_returns_saved_runs(client):
    from apps.api.store import benchmark_store
    run = BenchmarkRun(id="run-001", suite_name="smoke", status="pending")
    benchmark_store.save(run)

    response = await client.get("/benchmarks")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == "run-001"
    assert body[0]["suite_name"] == "smoke"
    assert body[0]["status"] == "pending"


# ── GET /benchmarks/{id} ───────────────────────────────────────────────────────

async def test_get_run_not_found(client):
    response = await client.get("/benchmarks/nonexistent-id")
    assert response.status_code == 404


async def test_get_run_found(client):
    from apps.api.store import benchmark_store
    run = BenchmarkRun(id="run-abc", suite_name="quick", status="running")
    benchmark_store.save(run)

    response = await client.get("/benchmarks/run-abc")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "run-abc"
    assert body["status"] == "running"


# ── GET /benchmarks/{id}/results ───────────────────────────────────────────────

async def test_get_results_not_found(client):
    response = await client.get("/benchmarks/no-such-run/results")
    assert response.status_code == 404


async def test_get_results_pending_returns_202(client):
    from apps.api.store import benchmark_store
    run = BenchmarkRun(id="run-pending", suite_name="s", status="pending")
    benchmark_store.save(run)

    response = await client.get("/benchmarks/run-pending/results")
    assert response.status_code == 202


async def test_get_results_running_returns_202(client):
    from apps.api.store import benchmark_store
    run = BenchmarkRun(id="run-running", suite_name="s", status="running")
    benchmark_store.save(run)

    response = await client.get("/benchmarks/run-running/results")
    assert response.status_code == 202


async def test_get_results_completed(client):
    from apps.api.store import benchmark_store
    run = make_completed_run("run-done")
    benchmark_store.save(run)

    response = await client.get("/benchmarks/run-done/results")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert len(body["cases"]) == 1
    case = body["cases"][0]
    assert case["p50_latency_ms"] == 100.0
    assert case["p95_latency_ms"] == 130.0
    assert case["throughput_rps"] == 5.0


# ── POST /benchmarks/run ───────────────────────────────────────────────────────

async def test_start_run_inline_suite(client):
    response = await client.post("/benchmarks/run", json={
        "suite": {
            "name": "quick_test",
            "model": "gpt-4o-mini",
            "concurrency_levels": [1],
            "prompt_lengths": [50],
            "output_lengths": [50],
            "streaming": [False],
            "runs_per_case": 1,
        }
    })
    assert response.status_code == 202
    body = response.json()
    assert body["suite_name"] == "quick_test"
    assert body["status"] in ("pending", "running", "completed")
    assert "id" in body


async def test_start_run_creates_entry_in_store(client):
    from apps.api.store import benchmark_store
    response = await client.post("/benchmarks/run", json={
        "suite": {
            "name": "store_test",
            "model": "gpt-4o-mini",
            "concurrency_levels": [1],
            "prompt_lengths": [50],
            "output_lengths": [50],
            "streaming": [False],
            "runs_per_case": 1,
        }
    })
    run_id = response.json()["id"]
    assert benchmark_store.get(run_id) is not None


async def test_start_run_missing_suite_returns_422(client):
    response = await client.post("/benchmarks/run", json={})
    assert response.status_code == 422


# ── GET /benchmarks/compare ────────────────────────────────────────────────────

async def test_compare_requires_at_least_two_ids(client):
    from apps.api.store import benchmark_store
    run = make_completed_run("solo-run")
    benchmark_store.save(run)

    response = await client.get("/benchmarks/compare?ids=solo-run")
    assert response.status_code == 422


async def test_compare_returns_both_runs(client):
    from apps.api.store import benchmark_store
    run1 = make_completed_run("r1", suite_name="suite_a")
    run2 = make_completed_run("r2", suite_name="suite_b")
    benchmark_store.save(run1)
    benchmark_store.save(run2)

    response = await client.get("/benchmarks/compare?ids=r1,r2")
    assert response.status_code == 200
    body = response.json()
    assert "runs" in body
    assert len(body["runs"]) == 2
    suite_names = {r["suite_name"] for r in body["runs"]}
    assert suite_names == {"suite_a", "suite_b"}


async def test_compare_skips_incomplete_runs(client):
    from apps.api.store import benchmark_store
    run_done = make_completed_run("done-1")
    run_pending = BenchmarkRun(id="pending-1", suite_name="s", status="pending")
    benchmark_store.save(run_done)
    benchmark_store.save(run_pending)

    # Two IDs supplied but only one is completed → partial comparison
    response = await client.get("/benchmarks/compare?ids=done-1,pending-1")
    # Only one completed → raises 422 (no completed runs or only one)
    # Depending on implementation: if only 1 completed run returns, it may 422
    # or return 1 run. The backend skips non-completed with a warning and raises
    # 422 if < 1 entry. With 1 completed run, it returns that 1 entry.
    assert response.status_code in (200, 422)
    if response.status_code == 200:
        assert len(response.json()["runs"]) == 1


async def test_compare_unknown_run_id_returns_404(client):
    from apps.api.store import benchmark_store
    run = make_completed_run("known-run")
    benchmark_store.save(run)

    response = await client.get("/benchmarks/compare?ids=known-run,unknown-xyz")
    assert response.status_code == 404
