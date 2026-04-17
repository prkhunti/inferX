"""In-memory store for benchmark runs.

Holds BenchmarkRun objects keyed by run ID. Thread-safe for asyncio
(single-threaded event loop); replace with a DB-backed store in v2.
"""

from __future__ import annotations

from packages.benchmarks.runner import BenchmarkRun


class BenchmarkStore:
    def __init__(self) -> None:
        self._runs: dict[str, BenchmarkRun] = {}

    def save(self, run: BenchmarkRun) -> None:
        self._runs[run.id] = run

    def get(self, run_id: str) -> BenchmarkRun | None:
        return self._runs.get(run_id)

    def list_all(self) -> list[BenchmarkRun]:
        return sorted(
            self._runs.values(),
            key=lambda r: r.started_at or r.id,
            reverse=True,
        )


# Module-level singleton — shared across all requests in the process
benchmark_store = BenchmarkStore()
