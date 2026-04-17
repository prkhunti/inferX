from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.api.database import get_db
from apps.api.db_models import Request

logger = logging.getLogger(__name__)

router = APIRouter()


class RequestMetricResponse(BaseModel):
    queue_ms: float | None
    ttft_ms: float | None
    total_latency_ms: float | None
    prompt_tokens: int | None
    output_tokens: int | None
    tokens_per_sec: float | None
    success: bool
    error_message: str | None


class RequestResponse(BaseModel):
    id: str
    request_type: str
    model: str
    prompt_token_count: int | None
    requested_output_tokens: int
    status: str
    created_at: str
    metric: RequestMetricResponse | None


def _serialize(req: Request) -> RequestResponse:
    metric = None
    if req.metric:
        m = req.metric
        metric = RequestMetricResponse(
            queue_ms=m.queue_ms,
            ttft_ms=m.ttft_ms,
            total_latency_ms=m.total_latency_ms,
            prompt_tokens=m.prompt_tokens,
            output_tokens=m.output_tokens,
            tokens_per_sec=m.tokens_per_sec,
            success=m.success,
            error_message=m.error_message,
        )
    return RequestResponse(
        id=req.id,
        request_type=req.request_type,
        model=req.model,
        prompt_token_count=req.prompt_token_count,
        requested_output_tokens=req.requested_output_tokens,
        status=req.status,
        created_at=req.created_at.isoformat(),
        metric=metric,
    )


@router.get(
    "/{request_id}",
    response_model=RequestResponse,
    summary="Get a single request trace with latency metrics",
)
async def get_request(
    request_id: str,
    db: AsyncSession = Depends(get_db),
) -> RequestResponse:
    """Return the full trace for a single request."""
    result = await db.execute(
        select(Request)
        .options(selectinload(Request.metric))
        .where(Request.id == request_id)
    )
    req = result.scalar_one_or_none()
    if req is None:
        raise HTTPException(status_code=404, detail=f"Request {request_id!r} not found")
    return _serialize(req)


@router.get(
    "",
    response_model=list[RequestResponse],
    summary="List recent requests with metrics",
)
async def list_requests(
    model: str | None = None,
    request_type: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[RequestResponse]:
    """Return recent requests, optionally filtered by model or type."""
    query = (
        select(Request)
        .options(selectinload(Request.metric))
        .order_by(Request.created_at.desc())
        .limit(min(limit, 200))
    )
    if model:
        query = query.where(Request.model == model)
    if request_type:
        query = query.where(Request.request_type == request_type)

    result = await db.execute(query)
    return [_serialize(r) for r in result.scalars().all()]
