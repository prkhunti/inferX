"""Integration tests for system endpoints."""


async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "InferX"
    assert "version" in body


async def test_health_no_auth_required(client):
    """Health endpoint must be reachable without any credentials."""
    response = await client.get("/health")
    assert response.status_code == 200
