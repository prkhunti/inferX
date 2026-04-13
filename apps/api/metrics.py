from prometheus_client import Counter, Histogram, Info
from prometheus_fastapi_instrumentator import Instrumentator

# ── Custom application metrics ─────────────────────────────────────────────

INFERENCE_REQUESTS = Counter(
    "inferx_inference_requests_total",
    "Total inference requests by endpoint and model",
    labelnames=["endpoint", "model", "status"],
)

TTFT_HISTOGRAM = Histogram(
    "inferx_ttft_milliseconds",
    "Time to first token in milliseconds",
    labelnames=["model"],
    buckets=[10, 25, 50, 100, 200, 500, 1000, 2000, 5000],
)

TOTAL_LATENCY_HISTOGRAM = Histogram(
    "inferx_total_latency_milliseconds",
    "End-to-end request latency in milliseconds",
    labelnames=["model", "endpoint"],
    buckets=[50, 100, 250, 500, 1000, 2500, 5000, 10000, 30000],
)

TOKENS_PER_SEC_HISTOGRAM = Histogram(
    "inferx_tokens_per_second",
    "Output token throughput per request",
    labelnames=["model"],
    buckets=[5, 10, 20, 50, 100, 200, 500],
)

OUTPUT_TOKENS_HISTOGRAM = Histogram(
    "inferx_output_tokens",
    "Number of output tokens per request",
    labelnames=["model"],
    buckets=[16, 32, 64, 128, 256, 512, 1024, 2048],
)

APP_INFO = Info("inferx_app", "InferX application metadata")


def setup_metrics(app) -> None:
    """Attach prometheus-fastapi-instrumentator and expose /metrics."""
    APP_INFO.info({"version": app.version, "title": app.title})

    Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        excluded_handlers=["/metrics", "/health"],
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
