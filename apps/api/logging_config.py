import json
import logging
import sys
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    """Emit each log record as a single-line JSON object.

    Fields always present:
        ts        ISO-8601 UTC timestamp
        level     DEBUG / INFO / WARNING / ERROR / CRITICAL
        logger    logger name
        msg       formatted message

    Fields added when available:
        request_id   from LogRecord.request_id (set via extra={})
        exc          exception type + message (only on exceptions)
        trace        full traceback string (only on exceptions)
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }

        if hasattr(record, "request_id"):
            payload["request_id"] = record.request_id

        # Attach any extra fields passed via extra={"key": value}
        _SKIP = {
            "name", "msg", "args", "levelname", "levelno", "pathname",
            "filename", "module", "exc_info", "exc_text", "stack_info",
            "lineno", "funcName", "created", "msecs", "relativeCreated",
            "thread", "threadName", "processName", "process", "message",
            "request_id", "taskName",
        }
        for key, value in record.__dict__.items():
            if key not in _SKIP:
                payload[key] = value

        if record.exc_info:
            exc_type, exc_value, _ = record.exc_info
            payload["exc"] = f"{exc_type.__name__}: {exc_value}" if exc_type else str(exc_value)
            payload["trace"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging(debug: bool = False) -> None:
    """Replace the root handler with a JSON-emitting stream handler."""
    level = logging.DEBUG if debug else logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Suppress noisy third-party loggers
    for name in ("uvicorn.access", "httpx", "openai._base_client"):
        logging.getLogger(name).setLevel(logging.WARNING)
