import json
import logging
from typing import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from apps.api.dependencies import get_backend, get_tracker
from apps.api.metrics import (
    INFERENCE_REQUESTS,
    TTFT_HISTOGRAM,
    TOTAL_LATENCY_HISTOGRAM,
    TOKENS_PER_SEC_HISTOGRAM,
    OUTPUT_TOKENS_HISTOGRAM,
)
from packages.metrics.service import RequestRecord, metrics_service
from packages.schemas.requests import GenerateRequest
from packages.schemas.responses import UsageStats
from packages.scheduler.tracker import RequestLifecycle, RequestTracker
from packages.serving.openai_backend import OpenAIBackend

logger = logging.getLogger(__name__)

router = APIRouter()


def _sse(data: dict) -> str:
    """Format a dict as a Server-Sent Events data line."""
    return f"data: {json.dumps(data)}\n\n"


async def _token_stream(
    req: GenerateRequest,
    backend: OpenAIBackend,
    lifecycle: RequestLifecycle,
) -> AsyncIterator[str]:
    """
    Core generator:
      1. Yields token SSE events, marking TTFT on the first token.
      2. Persists metrics and yields a final [DONE] event on completion.
      3. On backend error, persists the error and yields an error event.
    """
    first_token_seen = False
    prompt_tokens = 0
    completion_tokens = 0

    try:
        async for chunk in backend.stream(
            prompt=req.prompt,
            model=req.model,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
        ):
            if chunk.is_final:
                prompt_tokens = chunk.prompt_tokens or 0
                completion_tokens = chunk.completion_tokens or 0
                break

            if not first_token_seen:
                lifecycle.mark_first_token()
                first_token_seen = True

            yield _sse({"token": chunk.token, "request_id": lifecycle.request_id})

    except Exception as exc:
        INFERENCE_REQUESTS.labels(endpoint="stream", model=req.model, status="error").inc()
        logger.exception(
            "stream.error",
            extra={"request_id": lifecycle.request_id, "model": req.model},
        )
        metrics_service.record(RequestRecord(
            request_id=lifecycle.request_id,
            request_type="stream",
            model=req.model,
            requested_output_tokens=req.max_tokens,
            status="error",
            error_message=str(exc),
        ))
        yield _sse({"error": str(exc), "request_id": lifecycle.request_id})
        return

    lifecycle.mark_complete()
    latency = lifecycle.to_latency_stats(completion_tokens)
    usage = UsageStats(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
    )

    # Prometheus
    INFERENCE_REQUESTS.labels(endpoint="stream", model=req.model, status="success").inc()
    TTFT_HISTOGRAM.labels(model=req.model).observe(latency.ttft_ms)
    TOTAL_LATENCY_HISTOGRAM.labels(model=req.model, endpoint="stream").observe(latency.total_latency_ms)
    TOKENS_PER_SEC_HISTOGRAM.labels(model=req.model).observe(latency.tokens_per_sec)
    OUTPUT_TOKENS_HISTOGRAM.labels(model=req.model).observe(completion_tokens)

    # Postgres (fire-and-forget)
    metrics_service.record(RequestRecord(
        request_id=lifecycle.request_id,
        request_type="stream",
        model=req.model,
        requested_output_tokens=req.max_tokens,
        status="success",
        usage=usage,
        latency=latency,
    ))

    logger.info(
        "stream.done",
        extra={
            "request_id": lifecycle.request_id,
            "model": req.model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "ttft_ms": latency.ttft_ms,
            "total_latency_ms": latency.total_latency_ms,
            "tokens_per_sec": latency.tokens_per_sec,
        },
    )

    yield _sse({
        "done": True,
        "request_id": lifecycle.request_id,
        "model": req.model,
        "usage": usage.model_dump(),
        "latency": latency.model_dump(),
    })

    yield "data: [DONE]\n\n"


@router.post(
    "",
    summary="Stream tokens via Server-Sent Events",
    response_class=StreamingResponse,
    responses={
        200: {"content": {"text/event-stream": {}}, "description": "SSE token stream"},
        502: {"description": "Backend error"},
    },
)
async def stream(
    req: GenerateRequest,
    backend: OpenAIBackend = Depends(get_backend),
    tracker: RequestTracker = Depends(get_tracker),
) -> StreamingResponse:
    """
    Submit a prompt and receive tokens as they are generated via Server-Sent Events.

    **SSE event types:**

    | Event | Shape |
    |-------|-------|
    | Token | `{"token": "...", "request_id": "..."}` |
    | Done  | `{"done": true, "request_id": "...", "usage": {...}, "latency": {...}}` |
    | Error | `{"error": "...", "request_id": "..."}` |
    | Terminal | `[DONE]` |
    """
    lifecycle = tracker.start_request()

    logger.info(
        "stream.start",
        extra={
            "request_id": lifecycle.request_id,
            "model": req.model,
            "prompt_len": len(req.prompt),
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
        },
    )

    return StreamingResponse(
        _token_stream(req, backend, lifecycle),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Request-Id": lifecycle.request_id,
        },
    )
