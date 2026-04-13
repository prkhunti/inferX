"""SQLAlchemy ORM table definitions."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Request(Base):
    __tablename__ = "requests"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    request_type: Mapped[str] = mapped_column(String(16), nullable=False)   # generate | stream
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_token_count: Mapped[int | None] = mapped_column(Integer)
    requested_output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)         # success | error
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        server_default=func.now(),
    )

    metric: Mapped["RequestMetric | None"] = relationship(
        "RequestMetric", back_populates="request", uselist=False, cascade="all, delete-orphan"
    )


class RequestMetric(Base):
    __tablename__ = "request_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(
        String, ForeignKey("requests.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Timing (milliseconds)
    queue_ms: Mapped[float | None] = mapped_column(Float)
    ttft_ms: Mapped[float | None] = mapped_column(Float)
    total_latency_ms: Mapped[float | None] = mapped_column(Float)

    # Token counts
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)

    # Derived
    tokens_per_sec: Mapped[float | None] = mapped_column(Float)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(512))

    request: Mapped["Request"] = relationship("Request", back_populates="metric")
