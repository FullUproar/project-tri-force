"""Stripe billing endpoints for ASC subscriptions."""

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logging import logger
from app.core.security import get_current_tenant
from app.dependencies import get_db
from app.models.database import Organization

stripe.api_key = settings.stripe_secret_key.get_secret_value()

router = APIRouter()


class CreateCheckoutRequest(BaseModel):
    success_url: str = "https://cortaloom.ai/billing?status=success"
    cancel_url: str = "https://cortaloom.ai/billing?status=cancel"


@router.post("/billing/checkout")
async def create_checkout_session(
    body: CreateCheckoutRequest,
    db: AsyncSession = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
):
    """Create a Stripe Checkout session for the ASC subscription."""
    if not settings.stripe_price_id:
        raise HTTPException(status_code=503, detail="Billing not configured")

    # Create or reuse Stripe customer
    if not tenant.stripe_customer_id:
        customer = stripe.Customer.create(
            name=tenant.name,
            metadata={"cortaloom_org_id": str(tenant.id)},
        )
        tenant.stripe_customer_id = customer.id
        await db.commit()

    session = stripe.checkout.Session.create(
        customer=tenant.stripe_customer_id,
        line_items=[{"price": settings.stripe_price_id, "quantity": 1}],
        mode="subscription",
        success_url=body.success_url,
        cancel_url=body.cancel_url,
        metadata={"cortaloom_org_id": str(tenant.id)},
    )

    return {"checkout_url": session.url}


@router.get("/billing/status")
async def get_billing_status(
    db: AsyncSession = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
):
    """Get the current subscription status for the tenant."""
    return {
        "organization": tenant.name,
        "subscription_status": tenant.subscription_status or "none",
        "stripe_customer_id": tenant.stripe_customer_id,
    }


@router.post("/billing/portal")
async def create_billing_portal(
    db: AsyncSession = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
):
    """Create a Stripe Customer Portal session for managing subscription."""
    if not tenant.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No active subscription")

    session = stripe.billing_portal.Session.create(
        customer=tenant.stripe_customer_id,
        return_url="https://cortaloom.ai/billing",
    )

    return {"portal_url": session.url}


# --- Webhook (no auth — Stripe signs these) ---


async def handle_stripe_webhook(request: Request, db: AsyncSession):
    """Process Stripe webhook events to update subscription status."""
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    webhook_secret = settings.stripe_webhook_secret.get_secret_value()

    if webhook_secret:
        try:
            event = stripe.Webhook.construct_event(payload, sig, webhook_secret)
        except stripe.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
    else:
        # Dev mode — no signature verification
        import json
        event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)

    event_type = event.type
    data = event.data.object

    if event_type in (
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    ):
        customer_id = data.get("customer")
        status = data.get("status")  # active, past_due, canceled, trialing, etc.

        result = await db.execute(
            select(Organization).where(Organization.stripe_customer_id == customer_id)
        )
        org = result.scalar_one_or_none()
        if org:
            org.subscription_status = status
            await db.commit()
            logger.info("Updated subscription for %s: %s", org.name, status)

    return JSONResponse({"status": "ok"})
