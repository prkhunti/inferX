from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from openai import APIStatusError

from apps.api.dependencies import get_backend, get_tracker
from apps.api.metrics import (
    INFERENCE_REQUESTS,
    OUTPUT_TOKENS_HISTOGRAM,
    TOKENS_PER_SEC_HISTOGRAM,
    TOTAL_LATENCY_HISTOGRAM,
)
from packages.metrics.service import RequestRecord, metrics_service
from packages.scheduler.tracker import RequestTracker
from packages.schemas.requests import GenerateRequest
from packages.schemas.responses import GenerateResponse, UsageStats
from packages.serving.openai_backend import OpenAIBackend

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", response_model=GenerateResponse, summary="Run a synchronous generation")
async def generate(
    req: GenerateRequest,
    backend: OpenAIBackend = Depends(get_backend),
    tracker: RequestTracker = Depends(get_tracker),
) -> GenerateResponse:
    """
    Submit a prompt and receive the full generated response along with
    latency and usage statistics.
    """
    lifecycle = tracker.start_request()

    logger.info(
        "generate.start",
        extra={
            "request_id": lifecycle.request_id,
            "model": req.model,
            "prompt_len": len(req.prompt),
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
        },
    )

    try:
        result = await backend.generate(
            prompt=req.prompt,
            model=req.model,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
        )
    except APIStatusError as exc:
        INFERENCE_REQUESTS.labels(endpoint="generate", model=req.model, status="error").inc()
        logger.exception(
            "generate.error",
            extra={
                "request_id": lifecycle.request_id,
                "model": req.model,
                "status_code": exc.status_code,
            },
        )
        metrics_service.record(RequestRecord(
            request_id=lifecycle.request_id,
            request_type="generate",
            model=req.model,
            requested_output_tokens=req.max_tokens,
            status="error",
            error_message=exc.message,
        ))
        raise HTTPException(status_code=502, detail=exc.message) from exc
    except Exception as exc:
        INFERENCE_REQUESTS.labels(endpoint="generate", model=req.model, status="error").inc()
        logger.exception(
            "generate.error",
            extra={"request_id": lifecycle.request_id, "model": req.model},
        )
        metrics_service.record(RequestRecord(
            request_id=lifecycle.request_id,
            request_type="generate",
            model=req.model,
            requested_output_tokens=req.max_tokens,
            status="error",
            error_message=str(exc),
        ))
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    lifecycle.mark_first_token()
    lifecycle.mark_complete()

    latency = lifecycle.to_latency_stats(result.completion_tokens)
    usage = UsageStats(
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        total_tokens=result.prompt_tokens + result.completion_tokens,
    )

    # Prometheus
    INFERENCE_REQUESTS.labels(endpoint="generate", model=req.model, status="success").inc()
    TOTAL_LATENCY_HISTOGRAM.labels(model=req.model, endpoint="generate").observe(
        latency.total_latency_ms
    )
    TOKENS_PER_SEC_HISTOGRAM.labels(model=req.model).observe(latency.tokens_per_sec)
    OUTPUT_TOKENS_HISTOGRAM.labels(model=req.model).observe(result.completion_tokens)

    # Postgres (fire-and-forget)
    metrics_service.record(RequestRecord(
        request_id=lifecycle.request_id,
        request_type="generate",
        model=req.model,
        requested_output_tokens=req.max_tokens,
        status="success",
        usage=usage,
        latency=latency,
    ))

    logger.info(
        "generate.done",
        extra={
            "request_id": lifecycle.request_id,
            "model": req.model,
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "queue_ms": latency.queue_ms,
            "ttft_ms": latency.ttft_ms,
            "total_latency_ms": latency.total_latency_ms,
            "tokens_per_sec": latency.tokens_per_sec,
        },
    )

    return GenerateResponse(
        request_id=lifecycle.request_id,
        model=req.model,
        text=result.text,
        usage=usage,
        latency=latency,
    )
