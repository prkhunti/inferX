import logging

from apps.api.config import get_settings
from packages.scheduler.tracker import RequestTracker
from packages.serving.base import BaseBackend
from packages.serving.echo_backend import EchoBackend
from packages.serving.openai_backend import OpenAIBackend

logger = logging.getLogger(__name__)

_settings = get_settings()


def _build_backend() -> BaseBackend:
    backend_type = _settings.backend_type.lower()
    if backend_type == "echo":
        logger.info("inferx.backend type=echo")
        return EchoBackend()
    if backend_type == "openai":
        logger.info(
            "inferx.backend type=openai base_url=%s",
            _settings.openai_base_url,
        )
        return OpenAIBackend(
            api_key=_settings.openai_api_key,
            base_url=_settings.openai_base_url,
        )
    raise ValueError(
        f"Unknown BACKEND_TYPE={backend_type!r}. Valid values: 'openai', 'echo'."
    )


_backend: BaseBackend = _build_backend()


def get_backend() -> BaseBackend:
    return _backend


def get_tracker() -> RequestTracker:
    return RequestTracker()
