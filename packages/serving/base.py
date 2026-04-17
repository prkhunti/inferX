from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass
class BackendResponse:
    text: str
    prompt_tokens: int
    completion_tokens: int


@dataclass
class StreamChunk:
    """A single chunk from a streaming generation.

    For intermediate chunks: token is set, usage fields are None.
    For the final sentinel chunk: token is empty, usage fields are set.
    """
    token: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None

    @property
    def is_final(self) -> bool:
        return self.prompt_tokens is not None


class BaseBackend(ABC):
    """Abstract base for all model serving backends.

    Implementations: OpenAIBackend, vLLMBackend, LlamaCppBackend, ...
    """

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> BackendResponse:
        """Run a full (non-streaming) generation and return the complete response."""

    @abstractmethod
    def stream(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[StreamChunk]:
        """Yield StreamChunk objects. The last chunk has is_final=True and carries usage."""
