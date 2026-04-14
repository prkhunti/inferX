"""Echo backend — zero-latency stub that never calls any external API.

Use this backend for local development and CI when no API key is available.
Set BACKEND_TYPE=echo in the environment (the default in docker-compose).

Latency model
-------------
generate():  50 ms base  +  10 ms per 100 output tokens (max_tokens)
stream():    5 ms per token yielded

Token counts
------------
prompt_tokens     = max(1, len(prompt) // 4)   # ~4 chars/token (GPT approximation)
completion_tokens = max(1, max_tokens // 3)     # use one-third of the requested budget
"""

from __future__ import annotations

import asyncio
import itertools
from typing import AsyncIterator

from .base import BackendResponse, BaseBackend, StreamChunk

# ── Tuneable latency knobs ────────────────────────────────────────────────────
_GENERATE_BASE_MS: float = 50.0
_GENERATE_PER_100_TOKENS_MS: float = 10.0
_STREAM_PER_TOKEN_MS: float = 5.0

# ── Canned sentences cycled across calls ─────────────────────────────────────
_CANNED: list[str] = [
    "The quick brown fox jumps over the lazy dog near the riverbank.",
    "Machine learning models trade off latency, throughput, and cost at every scale.",
    "Benchmarking inference infrastructure reveals bottlenecks invisible in development.",
    "Distributed systems require careful coordination to achieve consistent performance.",
    "Token generation speed depends on model size, quantization, and hardware utilisation.",
]
_sentence_cycle = itertools.cycle(_CANNED)


def _next_sentence() -> str:
    return next(_sentence_cycle)


class EchoBackend(BaseBackend):
    """Fully local backend for development and CI.  Never makes network calls."""

    async def generate(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> BackendResponse:
        delay_s = (_GENERATE_BASE_MS + (max_tokens / 100) * _GENERATE_PER_100_TOKENS_MS) / 1000
        await asyncio.sleep(delay_s)

        prompt_tokens = max(1, len(prompt) // 4)
        completion_tokens = max(1, max_tokens // 3)

        return BackendResponse(
            text=_next_sentence(),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    async def stream(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[StreamChunk]:
        prompt_tokens = max(1, len(prompt) // 4)
        sentence = _next_sentence()
        words = sentence.split()

        for word in words:
            await asyncio.sleep(_STREAM_PER_TOKEN_MS / 1000)
            yield StreamChunk(token=word + " ")

        # Final sentinel carries usage stats — mirrors OpenAIBackend's final chunk
        completion_tokens = max(1, max_tokens // 3)
        yield StreamChunk(
            token="",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
