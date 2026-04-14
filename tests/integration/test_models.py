"""Integration tests for GET /models."""

import pytest
from packages.schemas.model_profile import ModelProfile, ModelRegistry


async def test_models_returns_list(client):
    response = await client.get("/models")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


async def test_models_with_registered_profile(client):
    """Register a profile directly on the module-level registry and verify it appears."""
    from packages.schemas.model_profile import model_registry

    profile = ModelProfile(
        name="test-model",
        provider="test",
        model_id="test-model-id",
        parameter_size="~1B",
        backend_type="openai",
        max_context_tokens=4096,
        max_output_tokens=1024,
        cost_per_1k_input_tokens=0.001,
        cost_per_1k_output_tokens=0.002,
    )
    model_registry._profiles["test-model"] = profile

    try:
        response = await client.get("/models")
        assert response.status_code == 200
        names = [m["name"] for m in response.json()]
        assert "test-model" in names

        # Verify shape of returned profile
        test_entry = next(m for m in response.json() if m["name"] == "test-model")
        assert test_entry["provider"] == "test"
        assert test_entry["model_id"] == "test-model-id"
        assert test_entry["cost_per_1k_input_tokens"] == 0.001
        assert test_entry["cost_per_1k_output_tokens"] == 0.002
    finally:
        model_registry._profiles.pop("test-model", None)


async def test_model_profile_estimate_cost():
    """Unit-level: ModelProfile.estimate_cost returns correct USD value."""
    profile = ModelProfile(
        name="m",
        provider="openai",
        model_id="gpt-4o-mini",
        cost_per_1k_input_tokens=0.15,   # $0.15 / 1k
        cost_per_1k_output_tokens=0.60,  # $0.60 / 1k
    )
    # 1000 input + 500 output
    cost = profile.estimate_cost(prompt_tokens=1000, completion_tokens=500)
    expected = (1000 / 1000) * 0.15 + (500 / 1000) * 0.60
    assert cost == pytest.approx(expected, abs=1e-8)


async def test_model_profile_zero_cost():
    profile = ModelProfile(
        name="free",
        provider="local",
        model_id="llama-3",
        cost_per_1k_input_tokens=0.0,
        cost_per_1k_output_tokens=0.0,
    )
    assert profile.estimate_cost(100, 100) == 0.0
