import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Paths that generate too much noise at INFO level
_SILENT_PATHS = {"/health", "/metrics", "/favicon.ico"}


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Per-request structured logging with timing.

    For every HTTP request this middleware:
      1. Reads or generates an X-Request-ID.
      2. Times the full round-trip (wall-clock, including streaming).
      3. Emits a single structured log line on completion with:
           request_id, method, path, status_code, duration_ms, client_ip
      4. Echoes X-Request-ID back in the response headers.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        start = time.perf_counter()

        # Stash on the request state so route handlers can read it
        request.state.request_id = request_id

        response: Response = await call_next(request)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Request-Id"] = request_id
        response.headers["X-Response-Time-Ms"] = str(duration_ms)

        path = request.url.path
        if path not in _SILENT_PATHS:
            logger.info(
                "%s %s %s %.1fms",
                request.method,
                path,
                response.status_code,
                duration_ms,
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "client_ip": _client_ip(request),
                    "query": str(request.query_params) or None,
                },
            )

        return response


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"
