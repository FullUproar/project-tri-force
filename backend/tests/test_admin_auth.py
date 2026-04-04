"""Admin authorization tests.

Verifies that admin endpoints are properly gated by is_admin flag.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.orm import selectinload

from app.core.db import async_session
from app.core.security import hash_api_key
from app.main import app
from app.models.database import ApiKey, Organization


async def _ensure_tenant(name: str, api_key_raw: str, is_admin: bool = False) -> str:
    """Create or fetch a tenant for testing. Returns org_id."""
    from datetime import datetime, timezone

    from sqlalchemy import select

    async with async_session() as db:
        existing = await db.execute(
            select(ApiKey)
            .options(selectinload(ApiKey.organization))
            .where(ApiKey.key_hash == hash_api_key(api_key_raw))
            .limit(1)
        )
        existing_key = existing.scalar_one_or_none()
        if existing_key:
            if existing_key.organization:
                existing_key.organization.is_admin = is_admin
                if not existing_key.organization.baa_signed_at:
                    existing_key.organization.baa_signed_at = datetime.now(timezone.utc)
                await db.commit()
                return str(existing_key.organization.id)
            return ""

        org = Organization(
            name=name,
            baa_signed_at=datetime.now(timezone.utc),
            is_admin=is_admin,
        )
        db.add(org)
        await db.flush()

        key = ApiKey(
            organization_id=org.id,
            key_hash=hash_api_key(api_key_raw),
            name=f"{name} key",
        )
        db.add(key)
        await db.commit()
        return str(org.id)


ADMIN_KEY = "test-admin-key-for-auth-test"
NON_ADMIN_KEY = "test-nonadmin-key-for-auth-test"


@pytest.mark.asyncio
async def test_admin_endpoint_allowed_for_admin():
    """Admin users can access admin endpoints."""
    await _ensure_tenant("Admin Org", ADMIN_KEY, is_admin=True)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/admin/organizations",
            headers={"X-API-Key": ADMIN_KEY},
        )
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_endpoint_denied_for_non_admin():
    """Non-admin users get 403 on admin endpoints."""
    await _ensure_tenant("Regular ASC", NON_ADMIN_KEY, is_admin=False)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/admin/organizations",
            headers={"X-API-Key": NON_ADMIN_KEY},
        )
        assert resp.status_code == 403
        assert "admin" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_org_denied_for_non_admin():
    """Non-admin cannot create organizations."""
    await _ensure_tenant("Regular ASC 2", NON_ADMIN_KEY, is_admin=False)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/admin/organizations",
            headers={"X-API-Key": NON_ADMIN_KEY},
            json={"name": "Should Not Create"},
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_me_endpoint_accessible_to_all():
    """/me endpoint should work for any authenticated user."""
    await _ensure_tenant("Any User Org", NON_ADMIN_KEY, is_admin=False)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/me",
            headers={"X-API-Key": NON_ADMIN_KEY},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "is_admin" in data
        assert data["is_admin"] is False


@pytest.mark.asyncio
async def test_baa_required():
    """Endpoints should return 403 if BAA not signed."""
    from datetime import datetime, timezone
    from sqlalchemy import select

    baa_key = "test-no-baa-key-12345"
    async with async_session() as db:
        existing = await db.execute(
            select(ApiKey).where(ApiKey.key_hash == hash_api_key(baa_key)).limit(1)
        )
        if not existing.scalar_one_or_none():
            org = Organization(name="No BAA Org", baa_signed_at=None)
            db.add(org)
            await db.flush()
            key = ApiKey(
                organization_id=org.id,
                key_hash=hash_api_key(baa_key),
                name="No BAA key",
            )
            db.add(key)
            await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/ingest/jobs",
            headers={"X-API-Key": baa_key},
        )
        assert resp.status_code == 403
        assert "Business Associate Agreement" in resp.json()["detail"]
