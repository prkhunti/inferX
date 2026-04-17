from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from packages.schemas.responses import LatencyStats


@dataclass
class RequestLifecycle:
    """Track the lifecycle timestamps for a single request."""

    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    enqueue_time: float = field(default_factory=time.perf_counter)
    start_time: float | None = None
    first_token_time: float | None = None
    completion_time: float | None = None

    def mark_start(self) -> None:
        self.start_time = time.perf_counter()

    def mark_first_token(self) -> None:
        self.first_token_time = time.perf_counter()

    def mark_complete(self) -> None:
        self.completion_time = time.perf_counter()

    def to_latency_stats(self, completion_tokens: int) -> LatencyStats:
        """Convert the captured lifecycle timestamps into latency statistics."""
        now = time.perf_counter()
        start = self.start_time or now
        first_token = self.first_token_time or now
        complete = self.completion_time or now

        queue_ms = (start - self.enqueue_time) * 1000
        ttft_ms = (first_token - start) * 1000
        total_latency_ms = (complete - self.enqueue_time) * 1000

        generation_sec = complete - first_token
        tokens_per_sec = (
            completion_tokens / generation_sec if generation_sec > 0 else 0.0
        )

        return LatencyStats(
            queue_ms=round(queue_ms, 2),
            ttft_ms=round(ttft_ms, 2),
            total_latency_ms=round(total_latency_ms, 2),
            tokens_per_sec=round(tokens_per_sec, 2),
        )


class RequestTracker:
    """Creates and manages RequestLifecycle objects for in-flight requests."""

    def start_request(self) -> RequestLifecycle:
        lc = RequestLifecycle()
        lc.mark_start()
        return lc
