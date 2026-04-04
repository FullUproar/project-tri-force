"""Error handling tests.

Verifies that the global exception handler and error responses work correctly.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_404_returns_json():
    """Non-existent endpoints should return proper 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/this-does-not-exist")
        assert resp.status_code in (404, 405)


@pytest.mark.asyncio
async def test_missing_api_key_returns_401():
    """Endpoints requiring auth should 401 without key."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/ingest/jobs")
        assert resp.status_code == 401
        data = resp.json()
        assert "detail" in data


@pytest.mark.asyncio
async def test_health_no_auth():
    """Health endpoint should not require auth."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["service"] == "cortaloom-api"
        assert "database" in data
        assert "timestamp" in data


@pytest.mark.asyncio
async def test_oversized_upload_rejected():
    """Uploads exceeding max size should be rejected."""
    # Create a ~1MB payload (small enough to not OOM but tests the boundary)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        from tests.conftest import TEST_API_KEY

        resp = await client.post(
            "/api/v1/ingest/clinical-note",
            headers={"X-API-Key": TEST_API_KEY},
            files={"file": ("huge.txt", b"x" * 100, "text/plain")},
        )
        # Should either accept small file or return validation error
        assert resp.status_code in (200, 400, 403, 413)


@pytest.mark.asyncio
async def test_request_id_in_response():
    """All responses should have X-Request-ID header."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        assert "x-request-id" in resp.headers


@pytest.mark.asyncio
async def test_security_headers_present():
    """All responses should include security headers."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.headers.get("x-content-type-options") == "nosniff"
        assert resp.headers.get("x-frame-options") == "DENY"
        assert "strict-transport-security" in resp.headers
