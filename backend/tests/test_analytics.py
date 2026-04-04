"""Analytics endpoint tests."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.orm import selectinload

from app.core.db import async_session
from app.core.security import hash_api_key
from app.main import app
from app.models.database import ApiKey, Organization


ANALYTICS_KEY = "test-analytics-key-77777"


async def _ensure_analytics_tenant():
    from datetime import datetime, timezone
    from sqlalchemy import select

    async with async_session() as db:
        existing = await db.execute(
            select(ApiKey)
            .options(selectinload(ApiKey.organization))
            .where(ApiKey.key_hash == hash_api_key(ANALYTICS_KEY))
            .limit(1)
        )
        if existing.scalar_one_or_none():
            return

        org = Organization(
            name="Analytics Test ASC",
            baa_signed_at=datetime.now(timezone.utc),
        )
        db.add(org)
        await db.flush()

        key = ApiKey(
            organization_id=org.id,
            key_hash=hash_api_key(ANALYTICS_KEY),
            name="Analytics test key",
        )
        db.add(key)
        await db.commit()


@pytest.mark.asyncio
async def test_outcomes_empty():
    """Outcomes endpoint returns valid structure with no data."""
    await _ensure_analytics_tenant()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/analytics/outcomes",
            headers={"X-API-Key": ANALYTICS_KEY},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_with_outcome"] == 0
        assert data["approved"] == 0
        assert data["denied"] == 0


@pytest.mark.asyncio
async def test_usage_stats_empty():
    """Usage stats returns valid structure with no data."""
    await _ensure_analytics_tenant()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/analytics/usage",
            headers={"X-API-Key": ANALYTICS_KEY},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_jobs"] == 0
        assert data["total_extractions"] == 0
        assert data["estimated_time_saved_minutes"] == 0


@pytest.mark.asyncio
async def test_outcomes_by_diagnosis_empty():
    """Outcomes by diagnosis returns empty list with no data."""
    await _ensure_analytics_tenant()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/analytics/outcomes-by-diagnosis",
            headers={"X-API-Key": ANALYTICS_KEY},
        )
        assert resp.status_code == 200
        assert resp.json() == []


@pytest.mark.asyncio
async def test_override_stats_empty():
    """Override stats returns valid structure with no data."""
    await _ensure_analytics_tenant()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/analytics/overrides",
            headers={"X-API-Key": ANALYTICS_KEY},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_overrides"] == 0
        assert data["ai_accuracy_proxy"] == 100
