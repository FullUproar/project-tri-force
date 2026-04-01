import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint_returns_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "cortaloom-api"
    assert data["version"] == "0.1.0"
    assert "status" in data
    assert "database" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_health_never_returns_500():
    """Health endpoint must return 200 even if DB is down — status will be 'degraded'."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] in ("ok", "degraded")
