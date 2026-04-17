from __future__ import annotations

from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from .base import BackendResponse, BaseBackend, StreamChunk


class OpenAIBackend(BaseBackend):
    """OpenAI-compatible backend (works with OpenAI, Together, Groq, etc.)."""

    def __init__(self, api_key: str, base_url: str | None = None) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def generate(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> BackendResponse:
        response = await self._client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )

        choice = response.choices[0]
        usage = response.usage
        prompt_tokens = usage.prompt_tokens if usage is not None else 0
        completion_tokens = usage.completion_tokens if usage is not None else 0

        return BackendResponse(
            text=choice.message.content or "",
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
        """Yield token StreamChunks, followed by a final chunk carrying usage stats.

        Uses stream_options={"include_usage": True} so the API returns a usage
        object on the last chunk instead of requiring a separate call.
        """
        response = await self._client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            stream_options={"include_usage": True},
        )

        async for chunk in response:
            # Final chunk from OpenAI carries usage and an empty choices list
            if chunk.usage is not None:
                yield StreamChunk(
                    token="",
                    prompt_tokens=chunk.usage.prompt_tokens,
                    completion_tokens=chunk.usage.completion_tokens,
                )
                return

            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta.content
            if delta:
                yield StreamChunk(token=delta)
