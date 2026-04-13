"""MetricsService — persists request and latency data to Postgres.

Writes are fire-and-forget: launched as asyncio tasks so they never add
latency to the inference response path. Failures are logged but not raised.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

from packages.schemas.responses import LatencyStats, UsageStats

logger = logging.getLogger(__name__)


@dataclass
class RequestRecord:
    request_id: str
    request_type: str        # "generate" | "stream"
    model: str
    requested_output_tokens: int
    status: str              # "success" | "error"
    usage: Optional[UsageStats] = None
    latency: Optional[LatencyStats] = None
    error_message: Optional[str] = None


class MetricsService:
    """Thin async wrapper around DB writes for request metrics."""

    def record(self, record: RequestRecord) -> None:
        """Schedule a non-blocking DB write.  Call from any async context."""
        asyncio.create_task(self._write(record))

    async def _write(self, record: RequestRecord) -> None:
        try:
            # Import here to avoid circular imports at module load time
            from apps.api.database import get_session
            from apps.api.db_models import Request, RequestMetric

            async with get_session() as session:
                req = Request(
                    id=record.request_id,
                    request_type=record.request_type,
                    model=record.model,
                    prompt_token_count=record.usage.prompt_tokens if record.usage else None,
                    requested_output_tokens=record.requested_output_tokens,
                    status=record.status,
                )
                session.add(req)
                await session.flush()  # obtain the PK before inserting metrics

                metric = RequestMetric(
                    request_id=record.request_id,
                    queue_ms=record.latency.queue_ms if record.latency else None,
                    ttft_ms=record.latency.ttft_ms if record.latency else None,
                    total_latency_ms=record.latency.total_latency_ms if record.latency else None,
                    prompt_tokens=record.usage.prompt_tokens if record.usage else None,
                    output_tokens=record.usage.completion_tokens if record.usage else None,
                    tokens_per_sec=record.latency.tokens_per_sec if record.latency else None,
                    success=record.status == "success",
                    error_message=record.error_message,
                )
                session.add(metric)

            logger.debug(
                "metrics.saved request_id=%s type=%s status=%s",
                record.request_id,
                record.request_type,
                record.status,
            )

        except Exception as exc:
            logger.warning(
                "metrics.write_failed request_id=%s error=%s",
                record.request_id,
                exc,
            )


# Module-level singleton
metrics_service = MetricsService()
