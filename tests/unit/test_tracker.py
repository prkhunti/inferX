"""Unit tests for packages/scheduler/tracker.py."""

import time
import pytest
from packages.scheduler.tracker import RequestLifecycle, RequestTracker


class TestRequestLifecycle:
    def test_request_id_is_uuid(self):
        lc = RequestLifecycle()
        import uuid
        uuid.UUID(lc.request_id)  # raises ValueError if invalid

    def test_unique_ids(self):
        ids = {RequestLifecycle().request_id for _ in range(100)}
        assert len(ids) == 100

    def test_enqueue_time_set_on_creation(self):
        before = time.perf_counter()
        lc = RequestLifecycle()
        after = time.perf_counter()
        assert before <= lc.enqueue_time <= after

    def test_initial_state(self):
        lc = RequestLifecycle()
        assert lc.start_time is None
        assert lc.first_token_time is None
        assert lc.completion_time is None

    def test_mark_start(self):
        lc = RequestLifecycle()
        lc.mark_start()
        assert lc.start_time is not None
        assert lc.start_time >= lc.enqueue_time

    def test_mark_first_token(self):
        lc = RequestLifecycle()
        lc.mark_start()
        lc.mark_first_token()
        assert lc.first_token_time is not None
        assert lc.first_token_time >= lc.start_time

    def test_mark_complete(self):
        lc = RequestLifecycle()
        lc.mark_start()
        lc.mark_first_token()
        lc.mark_complete()
        assert lc.completion_time is not None
        assert lc.completion_time >= lc.first_token_time

    def test_to_latency_stats_non_negative(self):
        lc = RequestLifecycle()
        lc.mark_start()
        lc.mark_first_token()
        lc.mark_complete()
        stats = lc.to_latency_stats(completion_tokens=50)
        assert stats.queue_ms >= 0
        assert stats.ttft_ms >= 0
        assert stats.total_latency_ms >= 0

    def test_total_latency_covers_queue(self):
        lc = RequestLifecycle()
        lc.mark_start()
        lc.mark_first_token()
        lc.mark_complete()
        stats = lc.to_latency_stats(completion_tokens=10)
        # total latency = queue + generation time ≥ queue alone
        assert stats.total_latency_ms >= stats.queue_ms

    def test_tokens_per_sec_zero_when_no_tokens(self):
        lc = RequestLifecycle()
        lc.mark_start()
        lc.mark_first_token()
        lc.mark_complete()
        stats = lc.to_latency_stats(completion_tokens=0)
        assert stats.tokens_per_sec == 0.0

    def test_tokens_per_sec_positive(self):
        lc = RequestLifecycle()
        lc.mark_start()
        time.sleep(0.01)   # ensure measurable generation time
        lc.mark_first_token()
        time.sleep(0.01)
        lc.mark_complete()
        stats = lc.to_latency_stats(completion_tokens=100)
        assert stats.tokens_per_sec > 0

    def test_to_latency_stats_units_are_ms(self):
        """Values must be in milliseconds, not seconds."""
        lc = RequestLifecycle()
        lc.mark_start()
        time.sleep(0.05)   # 50 ms
        lc.mark_first_token()
        time.sleep(0.05)
        lc.mark_complete()
        stats = lc.to_latency_stats(completion_tokens=10)
        # total latency should be around 100ms, definitely > 10 (not seconds)
        assert stats.total_latency_ms > 10

    def test_graceful_without_marks(self):
        """to_latency_stats should not raise even if marks are missing."""
        lc = RequestLifecycle()
        stats = lc.to_latency_stats(completion_tokens=5)
        assert stats.queue_ms >= 0
        assert stats.total_latency_ms >= 0


class TestRequestTracker:
    def test_start_request_returns_lifecycle(self):
        tracker = RequestTracker()
        lc = tracker.start_request()
        assert isinstance(lc, RequestLifecycle)

    def test_start_request_sets_start_time(self):
        tracker = RequestTracker()
        lc = tracker.start_request()
        assert lc.start_time is not None

    def test_each_request_has_unique_id(self):
        tracker = RequestTracker()
        ids = {tracker.start_request().request_id for _ in range(50)}
        assert len(ids) == 50
