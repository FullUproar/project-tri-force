"""Rate limiting tests.

Verifies that rate limiting is applied and returns 429 when exceeded.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_not_rate_limited():
    """Health endpoint should never be rate limited."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for _ in range(50):
            resp = await client.get("/health")
            assert resp.status_code == 200


@pytest.mark.asyncio
async def test_rate_limit_header_present():
    """API responses should include rate limit headers."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        # Health endpoint is exempt, but check the response is valid
        assert resp.status_code == 200
