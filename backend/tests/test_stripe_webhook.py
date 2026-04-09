"""Stripe webhook handler tests.

All Stripe API calls are mocked — no real Stripe usage.
Tests use the live Neon database (via app config).
"""

import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.db import async_session
from app.core.security import hash_api_key
from app.main import app
from app.models.database import Organization


async def _create_org_with_stripe(
    name: str, stripe_customer_id: str, tier: str = "professional"
) -> uuid.UUID:
    """Create an org with a Stripe customer ID for webhook testing."""
    from datetime import datetime, timezone

    async with async_session() as db:
        org = Organization(
            name=name,
            baa_signed_at=datetime.now(timezone.utc),
            stripe_customer_id=stripe_customer_id,
            subscription_tier=tier,
            subscription_status="active",
        )
        db.add(org)
        await db.commit()
        await db.refresh(org)
        return org.id


def _build_webhook_payload(
    event_type: str,
    customer_id: str,
    status: str = "active",
    tier: str | None = None,
) -> bytes:
    """Build a Stripe webhook event payload."""
    event = {
        "id": f"evt_{uuid.uuid4().hex[:24]}",
        "type": event_type,
        "data": {
            "object": {
                "customer": customer_id,
                "status": status,
                "metadata": {"tier": tier} if tier else {},
                "items": {"data": []},
            }
        },
    }
    return json.dumps(event).encode()


# ---------------------------------------------------------------------------
# Subscription created
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_webhook_subscription_created():
    """Webhook updates org when subscription is created."""
    cust_id = f"cus_test_{uuid.uuid4().hex[:12]}"
    org_id = await _create_org_with_stripe("Webhook Test ASC", cust_id, tier="starter")

    payload = _build_webhook_payload(
        "customer.subscription.created",
        cust_id,
        status="active",
        tier="professional",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/billing/webhook",
            content=payload,
            headers={"Content-Type": "application/json"},
        )

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    # Verify org was updated
    async with async_session() as db:
        org = await db.get(Organization, org_id)
        assert org.subscription_status == "active"
        assert org.subscription_tier == "professional"


# ---------------------------------------------------------------------------
# Subscription updated (downgrade)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_webhook_subscription_updated():
    """Webhook updates tier when subscription changes."""
    cust_id = f"cus_test_{uuid.uuid4().hex[:12]}"
    org_id = await _create_org_with_stripe("Upgrade Test ASC", cust_id, tier="professional")

    payload = _build_webhook_payload(
        "customer.subscription.updated",
        cust_id,
        status="active",
        tier="enterprise",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/billing/webhook",
            content=payload,
            headers={"Content-Type": "application/json"},
        )

    assert resp.status_code == 200

    async with async_session() as db:
        org = await db.get(Organization, org_id)
        assert org.subscription_tier == "enterprise"


# ---------------------------------------------------------------------------
# Subscription deleted (canceled)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_webhook_subscription_deleted():
    """Webhook sets status to canceled when subscription is deleted."""
    cust_id = f"cus_test_{uuid.uuid4().hex[:12]}"
    org_id = await _create_org_with_stripe("Cancel Test ASC", cust_id)

    payload = _build_webhook_payload(
        "customer.subscription.deleted",
        cust_id,
        status="canceled",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/billing/webhook",
            content=payload,
            headers={"Content-Type": "application/json"},
        )

    assert resp.status_code == 200

    async with async_session() as db:
        org = await db.get(Organization, org_id)
        assert org.subscription_status == "canceled"


# ---------------------------------------------------------------------------
# Unknown customer — graceful handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_webhook_unknown_customer_handled():
    """Webhook for an unknown customer ID returns 200 (no crash)."""
    payload = _build_webhook_payload(
        "customer.subscription.created",
        "cus_nonexistent_customer_99999",
        status="active",
        tier="starter",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/billing/webhook",
            content=payload,
            headers={"Content-Type": "application/json"},
        )

    # Should return ok — we just skip the unknown customer
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Unhandled event type — no crash
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_webhook_unhandled_event_type():
    """Unhandled event types return 200 without error."""
    event = {
        "id": f"evt_{uuid.uuid4().hex[:24]}",
        "type": "invoice.payment_succeeded",
        "data": {"object": {"customer": "cus_whatever"}},
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/billing/webhook",
            content=json.dumps(event).encode(),
            headers={"Content-Type": "application/json"},
        )

    assert resp.status_code == 200
