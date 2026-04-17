"""Integration tests for POST /generate."""

from unittest.mock import AsyncMock

from openai import RateLimitError


async def test_generate_success(client_with_backend):
    client, backend = client_with_backend
    response = await client.post("/generate", json={
        "prompt": "What is 2+2?",
        "model": "gpt-4o-mini",
        "temperature": 0.0,
        "max_tokens": 50,
        "stream": False,
    })
    assert response.status_code == 200
    body = response.json()

    assert body["text"] == "Paris is the capital of France."
    assert "request_id" in body
    assert body["model"] == "gpt-4o-mini"

    assert body["usage"]["prompt_tokens"] == 20
    assert body["usage"]["completion_tokens"] == 8
    assert body["usage"]["total_tokens"] == 28

    assert body["latency"]["total_latency_ms"] >= 0
    assert body["latency"]["ttft_ms"] >= 0
    assert body["latency"]["queue_ms"] >= 0


async def test_generate_calls_backend_with_correct_params(client_with_backend):
    client, backend = client_with_backend
    await client.post("/generate", json={
        "prompt": "Hello world",
        "model": "gpt-4o-mini",
        "temperature": 0.5,
        "max_tokens": 128,
        "stream": False,
    })
    backend.generate.assert_called_once_with(
        prompt="Hello world",
        model="gpt-4o-mini",
        temperature=0.5,
        max_tokens=128,
    )


async def test_generate_missing_prompt_returns_422(client):
    response = await client.post("/generate", json={
        "model": "gpt-4o-mini",
        "temperature": 0.0,
        "max_tokens": 50,
        "stream": False,
    })
    assert response.status_code == 422


async def test_generate_empty_prompt_returns_422(client):
    response = await client.post("/generate", json={
        "prompt": "",
        "model": "gpt-4o-mini",
        "temperature": 0.0,
        "max_tokens": 50,
        "stream": False,
    })
    assert response.status_code == 422


async def test_generate_backend_api_error_returns_502_with_clean_message(client_with_backend):
    """OpenAI APIStatusError should surface as a clean message, not a raw dict string."""
    client, backend = client_with_backend

    # Simulate an OpenAI RateLimitError (subclass of APIStatusError)
    backend.generate = AsyncMock(
        side_effect=RateLimitError(
            message="You exceeded your current quota",
            response=_make_mock_response(429),
            body={
                "error": {
                    "message": "You exceeded your current quota",
                    "code": "insufficient_quota",
                }
            },
        )
    )

    response = await client.post("/generate", json={
        "prompt": "test",
        "model": "gpt-4o-mini",
        "temperature": 0.0,
        "max_tokens": 50,
        "stream": False,
    })
    assert response.status_code == 502
    detail = response.json()["detail"]
    # Must be the human-readable message, not a raw Python dict repr
    assert "You exceeded your current quota" in detail
    assert "{'error'" not in detail   # no raw dict string


async def test_generate_generic_error_returns_502(client_with_backend):
    client, backend = client_with_backend
    backend.generate = AsyncMock(side_effect=RuntimeError("unexpected failure"))

    response = await client.post("/generate", json={
        "prompt": "test",
        "model": "gpt-4o-mini",
        "temperature": 0.0,
        "max_tokens": 50,
        "stream": False,
    })
    assert response.status_code == 502


# ── helpers ────────────────────────────────────────────────────────────────────

def _make_mock_response(status_code: int):
    """Minimal httpx.Response mock for constructing OpenAI errors in tests."""
    from unittest.mock import MagicMock

    import httpx

    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.headers = httpx.Headers({})
    resp.request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    return resp
