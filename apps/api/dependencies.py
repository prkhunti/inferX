from functools import lru_cache

from fastapi import Depends

from apps.api.config import Settings, get_settings
from packages.scheduler.tracker import RequestTracker
from packages.serving.openai_backend import OpenAIBackend


@lru_cache
def get_backend(settings: Settings = Depends(get_settings)) -> OpenAIBackend:
    return OpenAIBackend(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )


def get_tracker() -> RequestTracker:
    return RequestTracker()
