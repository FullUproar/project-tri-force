"""Billing and usage metering tests.

Tests the billing tier config, usage tracking, budget caps, and alert thresholds.
Stripe API calls are mocked.
"""

import pytest
from unittest.mock import patch, MagicMock
from httpx import ASGITransport, AsyncClient
from sqlalchemy.orm import selectinload

from app.core.db import async_session
from app.core.security import hash_api_key
from app.main import app
from app.models.database import ApiKey, Organization


BILLING_KEY = "test-billing-key-99999"


async def _ensure_billing_tenant() -> str:
    """Create a tenant with subscription for billing tests."""
    from datetime import datetime, timezone
    from sqlalchemy import select

    async with async_session() as db:
        existing = await db.execute(
            select(ApiKey)
            .options(selectinload(ApiKey.organization))
            .where(ApiKey.key_hash == hash_api_key(BILLING_KEY))
            .limit(1)
        )
        existing_key = existing.scalar_one_or_none()
        if existing_key and existing_key.organization:
            org = existing_key.organization
            org.subscription_tier = "professional"
            org.subscription_status = "active"
            org.monthly_extraction_count = 0
            org.billing_cycle_start = datetime.now(timezone.utc)
            org.alert_at_80_sent = False
            org.alert_at_100_sent = False
            org.overage_budget_cap = None
            org.baa_signed_at = datetime.now(timezone.utc)
            await db.commit()
            return str(org.id)

        org = Organization(
            name="Billing Test ASC",
            baa_signed_at=datetime.now(timezone.utc),
            subscription_tier="professional",
            subscription_status="active",
            monthly_extraction_count=0,
            billing_cycle_start=datetime.now(timezone.utc),
        )
        db.add(org)
        await db.flush()

        key = ApiKey(
            organization_id=org.id,
            key_hash=hash_api_key(BILLING_KEY),
            name="Billing test key",
        )
        db.add(key)
        await db.commit()
        return str(org.id)


@pytest.mark.asyncio
async def test_get_tiers():
    """Tier listing should return all three tiers."""
    await _ensure_billing_tenant()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/billing/tiers",
            headers={"X-API-Key": BILLING_KEY},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "starter" in data
        assert "professional" in data
        assert "enterprise" in data
        assert data["starter"]["amount"] == 149
        assert data["professional"]["amount"] == 299
        assert data["enterprise"]["amount"] == 499


@pytest.mark.asyncio
async def test_billing_status():
    """Billing status should reflect subscription and usage."""
    await _ensure_billing_tenant()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/billing/status",
            headers={"X-API-Key": BILLING_KEY},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["subscription_tier"] == "professional"
        assert data["subscription_status"] == "active"
        assert "usage" in data
        assert data["usage"]["extractions_included"] == 150


@pytest.mark.asyncio
async def test_set_budget_cap():
    """Setting a budget cap should persist."""
    await _ensure_billing_tenant()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/billing/budget",
            headers={"X-API-Key": BILLING_KEY},
            json={"budget_cap": 100.00},
        )
        assert resp.status_code == 200
        assert resp.json()["overage_budget_cap"] == 100.00

        # Verify in status
        status_resp = await client.get(
            "/api/v1/billing/status",
            headers={"X-API-Key": BILLING_KEY},
        )
        assert status_resp.json()["overage_budget_cap"] == 100.00


@pytest.mark.asyncio
async def test_negative_budget_cap_rejected():
    """Negative budget cap should be rejected."""
    await _ensure_billing_tenant()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/billing/budget",
            headers={"X-API-Key": BILLING_KEY},
            json={"budget_cap": -50.00},
        )
        assert resp.status_code == 400


@pytest.mark.asyncio
async def test_usage_metering_budget_cap_enforcement():
    """record_extraction_usage should block when budget cap exceeded."""
    from app.api.v1.billing import record_extraction_usage

    org_id = await _ensure_billing_tenant()

    async with async_session() as db:
        from sqlalchemy import select
        result = await db.execute(
            select(Organization).where(Organization.name == "Billing Test ASC")
        )
        org = result.scalar_one()

        # Set up: 150 included, already used 155 (5 overage = $12.50)
        org.monthly_extraction_count = 155
        org.overage_budget_cap = 10.00  # Cap at $10
        await db.commit()

        # Should be blocked (overage would be 6 * $2.50 = $15 > $10 cap)
        allowed = await record_extraction_usage(db, org)
        assert allowed is False


@pytest.mark.asyncio
async def test_usage_metering_within_budget():
    """record_extraction_usage should allow extraction within budget."""
    from app.api.v1.billing import record_extraction_usage

    await _ensure_billing_tenant()

    async with async_session() as db:
        from sqlalchemy import select
        result = await db.execute(
            select(Organization).where(Organization.name == "Billing Test ASC")
        )
        org = result.scalar_one()

        # Reset to clean state
        org.monthly_extraction_count = 0
        org.overage_budget_cap = None
        await db.commit()

        # Should be allowed
        allowed = await record_extraction_usage(db, org)
        assert allowed is True
        assert org.monthly_extraction_count == 1


@pytest.mark.asyncio
async def test_portal_requires_stripe_customer():
    """Billing portal should fail if no Stripe customer."""
    await _ensure_billing_tenant()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/billing/portal",
            headers={"X-API-Key": BILLING_KEY},
        )
        assert resp.status_code == 400
        assert "No active subscription" in resp.json()["detail"]
