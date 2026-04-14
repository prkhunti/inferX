# Set required env vars before any app imports so pydantic-settings is satisfied.
import os
os.environ.setdefault("OPENAI_API_KEY", "test-only-not-real")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool


# ── Silence MetricsService fire-and-forget tasks ──────────────────────────────

@pytest.fixture(autouse=True)
def no_metrics(monkeypatch):
    """Replace MetricsService.record with a no-op for all tests.

    MetricsService.record() spawns an asyncio.create_task that writes to the DB.
    In tests the SQLite engine is disposed before the task completes, causing
    'Cannot operate on a closed database' thread warnings.  A no-op avoids this
    without changing any application behaviour under test.
    """
    from packages.metrics.service import metrics_service
    monkeypatch.setattr(metrics_service, "record", lambda *_args, **_kwargs: None)

from packages.serving.base import BackendResponse, StreamChunk


# ── Mock backend ──────────────────────────────────────────────────────────────

def make_mock_backend(
    text: str = "Paris is the capital of France.",
    prompt_tokens: int = 20,
    completion_tokens: int = 8,
    stream_tokens: list[str] | None = None,
):
    """Return a mock BaseBackend with configurable responses."""
    backend = MagicMock()
    backend.generate = AsyncMock(
        return_value=BackendResponse(
            text=text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
    )

    tokens = stream_tokens or ["Hello", " world", "."]

    async def mock_stream(prompt, model, temperature, max_tokens):
        for token in tokens:
            yield StreamChunk(token=token)
        yield StreamChunk(token="", prompt_tokens=prompt_tokens, completion_tokens=len(tokens))

    backend.stream = mock_stream
    return backend


# ── DB fixtures ───────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db_setup():
    """
    Inject a shared in-memory SQLite engine into the app's database module.

    ASGITransport does not trigger the FastAPI lifespan, so init_db() is never
    called from the app.  We patch _engine and _session_factory directly so
    that both get_db (FastAPI dependency) and get_session (used by MetricsService)
    use the same test database.
    """
    import apps.api.database as db_module

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(db_module.Base.metadata.create_all)

    # Patch globals so all DB access in this test uses the test engine
    orig_engine = db_module._engine
    orig_factory = db_module._session_factory
    db_module._engine = engine
    db_module._session_factory = factory

    yield

    db_module._engine = orig_engine
    db_module._session_factory = orig_factory
    await engine.dispose()


# ── HTTP client fixture ───────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(db_setup):
    """Async httpx client wired to the FastAPI app with a mock backend."""
    from apps.api.main import app
    from apps.api.dependencies import get_backend
    from apps.api.store import benchmark_store

    backend = make_mock_backend()
    app.dependency_overrides[get_backend] = lambda: backend
    benchmark_store._runs.clear()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
    benchmark_store._runs.clear()


@pytest_asyncio.fixture
async def client_with_backend(db_setup):
    """
    Like `client` but yields (client, backend) so tests can inspect mock calls.
    """
    from apps.api.main import app
    from apps.api.dependencies import get_backend
    from apps.api.store import benchmark_store

    backend = make_mock_backend()
    app.dependency_overrides[get_backend] = lambda: backend
    benchmark_store._runs.clear()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac, backend

    app.dependency_overrides.clear()
    benchmark_store._runs.clear()
