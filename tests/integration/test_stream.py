"""Integration tests for POST /stream (SSE)."""

import json
import pytest
from unittest.mock import AsyncMock
from openai import RateLimitError

from packages.serving.base import StreamChunk


def parse_sse(response_text: str) -> list[dict]:
    """Parse raw SSE body into a list of event dicts (skips [DONE])."""
    events = []
    for line in response_text.splitlines():
        if not line.startswith("data: "):
            continue
        payload = line[len("data: "):].strip()
        if payload == "[DONE]":
            continue
        events.append(json.loads(payload))
    return events


async def test_stream_returns_200(client):
    response = await client.post("/stream", json={
        "prompt": "Count to three.",
        "model": "gpt-4o-mini",
        "temperature": 0.0,
        "max_tokens": 50,
        "stream": True,
    })
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]


async def test_stream_emits_token_events(client):
    response = await client.post("/stream", json={
        "prompt": "Say hello.",
        "model": "gpt-4o-mini",
        "temperature": 0.0,
        "max_tokens": 50,
        "stream": True,
    })
    events = parse_sse(response.text)

    token_events = [e for e in events if "token" in e]
    assert len(token_events) > 0, "Expected at least one token event"

    # Tokens should match the mock: ["Hello", " world", "."]
    tokens = [e["token"] for e in token_events]
    assert "Hello" in tokens


async def test_stream_emits_done_event(client):
    response = await client.post("/stream", json={
        "prompt": "test",
        "model": "gpt-4o-mini",
        "temperature": 0.0,
        "max_tokens": 50,
        "stream": True,
    })
    events = parse_sse(response.text)

    done_events = [e for e in events if e.get("done") is True]
    assert len(done_events) == 1

    done = done_events[0]
    assert "usage" in done
    assert "latency" in done
    assert "request_id" in done


async def test_stream_done_event_has_latency_fields(client):
    response = await client.post("/stream", json={
        "prompt": "test",
        "model": "gpt-4o-mini",
        "temperature": 0.0,
        "max_tokens": 50,
        "stream": True,
    })
    events = parse_sse(response.text)
    done = next(e for e in events if e.get("done"))

    for field in ("ttft_ms", "total_latency_ms", "queue_ms", "tokens_per_sec"):
        assert field in done["latency"], f"Missing latency field: {field}"


async def test_stream_done_event_has_usage_fields(client):
    response = await client.post("/stream", json={
        "prompt": "test",
        "model": "gpt-4o-mini",
        "temperature": 0.0,
        "max_tokens": 50,
        "stream": True,
    })
    events = parse_sse(response.text)
    done = next(e for e in events if e.get("done"))

    assert done["usage"]["prompt_tokens"] == 20    # from mock
    assert done["usage"]["completion_tokens"] == 3  # len(["Hello", " world", "."])


async def test_stream_tokens_followed_by_done(client):
    """All token events must precede the done event."""
    response = await client.post("/stream", json={
        "prompt": "test",
        "model": "gpt-4o-mini",
        "temperature": 0.0,
        "max_tokens": 50,
        "stream": True,
    })
    events = parse_sse(response.text)
    done_index = next(i for i, e in enumerate(events) if e.get("done"))

    for i, event in enumerate(events):
        if i < done_index:
            assert "token" in event, f"Expected token event at index {i}"


async def test_stream_error_event_on_backend_failure(client_with_backend):
    """Backend errors should produce an SSE error event, not an HTTP error."""
    client, backend = client_with_backend

    async def failing_stream(*args, **kwargs):
        raise RateLimitError(
            message="Rate limit exceeded",
            response=_make_mock_response(429),
            body={},
        )
        yield  # make it a generator

    backend.stream = failing_stream

    response = await client.post("/stream", json={
        "prompt": "test",
        "model": "gpt-4o-mini",
        "temperature": 0.0,
        "max_tokens": 50,
        "stream": True,
    })

    # HTTP layer still returns 200 (streaming started)
    assert response.status_code == 200

    events = parse_sse(response.text)
    error_events = [e for e in events if "error" in e]
    assert len(error_events) == 1
    # Error message should be clean (not raw dict)
    assert "Rate limit exceeded" in error_events[0]["error"]
    assert "{'error'" not in error_events[0]["error"]


# ── helpers ────────────────────────────────────────────────────────────────────

def _make_mock_response(status_code: int):
    from unittest.mock import MagicMock
    import httpx
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.headers = httpx.Headers({})
    resp.request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    return resp
