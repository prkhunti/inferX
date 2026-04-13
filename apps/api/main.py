from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.config import get_settings
from apps.api.database import close_db, init_db
from apps.api.logging_config import configure_logging
from apps.api.metrics import setup_metrics
from apps.api.middleware import RequestTimingMiddleware
from apps.api.routers import benchmarks, generate, models, requests, stream
from packages.schemas.model_profile import model_registry

settings = get_settings()
configure_logging(debug=settings.debug)

import logging  # noqa: E402 — must come after configure_logging
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(settings.database_url)
    model_registry.load_directory()
    logger.info(
        "inferx.startup",
        extra={"version": app.version, "models": model_registry.names()},
    )
    yield
    await close_db()
    logger.info("inferx.shutdown")


app = FastAPI(
    title=settings.app_name,
    description="Low-Latency LLM Inference and Benchmarking Platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Middleware (added in reverse priority order) ───────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestTimingMiddleware)

# ── Prometheus /metrics ────────────────────────────────────────────────────
setup_metrics(app)

# ── Routers ────────────────────────────────────────────────────────────────
app.include_router(generate.router, prefix="/generate", tags=["Inference"])
app.include_router(stream.router, prefix="/stream", tags=["Inference"])
app.include_router(benchmarks.router, prefix="/benchmarks", tags=["Benchmarks"])
app.include_router(models.router, prefix="/models", tags=["Models"])
app.include_router(requests.router, prefix="/requests", tags=["Observability"])


@app.get("/health", tags=["System"])
async def health() -> dict:
    return {"status": "ok", "service": settings.app_name, "version": app.version}
