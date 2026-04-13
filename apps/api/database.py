"""Async SQLAlchemy engine, session factory, and declarative Base."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)

# Populated by init_db() at startup
_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


class Base(DeclarativeBase):
    pass


def init_db(database_url: str) -> None:
    """Create the async engine and session factory.  Call once at startup."""
    global _engine, _session_factory

    _engine = create_async_engine(
        database_url,
        echo=False,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
    )
    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    logger.info("database.init url=%s", database_url.split("@")[-1])  # hide credentials


async def close_db() -> None:
    if _engine:
        await _engine.dispose()
        logger.info("database.closed")


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield a managed AsyncSession; roll back on exception."""
    if _session_factory is None:
        raise RuntimeError("Database not initialised — call init_db() first")

    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency — yields an AsyncSession."""
    async with get_session() as session:
        yield session
