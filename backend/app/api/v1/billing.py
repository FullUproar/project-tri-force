"""Stripe billing endpoints for tiered ASC subscriptions with usage metering."""

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

# Tier configuration — Stripe price IDs from our creation script
TIERS = {
    "starter": {
        "name": "Starter",
        "price_id": "price_1THb6g58OPvbpO2iq3Sv3p0p",
        "amount": 149,
        "included_extractions": 50,
        "description": "Small, single-specialty ASC",
    },
    "professional": {
        "name": "Professional",
        "price_id": "price_1THb6h58OPvbpO2iFGcWgV61",
        "amount": 299,
        "included_extractions": 150,
        "description": "2-4 OR multi-specialty ASC",
    },
    "enterprise": {
        "name": "Enterprise",
        "price_id": "price_1THb6h58OPvbpO2i0kmBVmSt",
        "amount": 499,
        "included_extractions": 350,
        "description": "High-volume facility",
    },
}

OVERAGE_PRICE_ID = "price_1THb6g58OPvbpO2ix0cLLjJX"
STRIPE_METER_EVENT_NAME = "cortaloom_extraction"


class CreateCheckoutRequest(BaseModel):
    tier: str = "professional"
    success_url: str = "https://cortaloom.ai/billing?status=success"
    cancel_url: str = "https://cortaloom.ai/billing?status=cancel"


@router.get("/billing/tiers")
async def get_tiers():
    """Return available pricing tiers."""
    return {
        tier_id: {
            "name": t["name"],
            "amount": t["amount"],
            "included_extractions": t["included_extractions"],
            "description": t["description"],
            "overage_rate": 2.50,
        }
        for tier_id, t in TIERS.items()
    }


@router.post("/billing/checkout")
async def create_checkout_session(
    body: CreateCheckoutRequest,
    db: AsyncSession = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
):
    """Create a Stripe Checkout session for the selected tier."""
    tier = TIERS.get(body.tier)
    if not tier:
        raise HTTPException(status_code=400, detail=f"Invalid tier. Choose: {list(TIERS.keys())}")

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
        line_items=[
            {"price": tier["price_id"], "quantity": 1},
            {"price": OVERAGE_PRICE_ID},  # Metered — no quantity
        ],
        mode="subscription",
        success_url=body.success_url,
        cancel_url=body.cancel_url,
        metadata={
            "cortaloom_org_id": str(tenant.id),
            "tier": body.tier,
        },
    )

    return {"checkout_url": session.url}


@router.get("/billing/status")
async def get_billing_status(
    db: AsyncSession = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
):
    """Get subscription status and usage for the current tenant."""
    tier_config = TIERS.get(tenant.subscription_tier or "", {})
    included = tier_config.get("included_extractions", 0)
    used = tenant.monthly_extraction_count or 0
    overage = max(0, used - included)

    return {
        "organization": tenant.name,
        "subscription_status": tenant.subscription_status or "none",
        "subscription_tier": tenant.subscription_tier,
        "stripe_customer_id": tenant.stripe_customer_id,
        "overage_budget_cap": tenant.overage_budget_cap,
        "usage": {
            "extractions_used": used,
            "extractions_included": included,
            "overage_count": overage,
            "overage_cost": round(overage * 2.50, 2),
            "budget_remaining": round(tenant.overage_budget_cap - (overage * 2.50), 2) if tenant.overage_budget_cap else None,
            "budget_exhausted": (overage * 2.50) >= tenant.overage_budget_cap if tenant.overage_budget_cap else False,
        },
    }


class SetBudgetCapRequest(BaseModel):
    budget_cap: float | None  # null = unlimited


@router.post("/billing/budget")
async def set_budget_cap(
    body: SetBudgetCapRequest,
    db: AsyncSession = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
):
    """Set or remove the monthly overage budget cap."""
    if body.budget_cap is not None and body.budget_cap < 0:
        raise HTTPException(status_code=400, detail="Budget cap must be positive or null")
    tenant.overage_budget_cap = body.budget_cap
    await db.commit()
    return {
        "status": "ok",
        "overage_budget_cap": tenant.overage_budget_cap,
        "message": f"Budget cap set to ${body.budget_cap:.2f}/month" if body.budget_cap else "Budget cap removed (unlimited)",
    }


@router.post("/billing/portal")
async def create_billing_portal(
    db: AsyncSession = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
):
    """Open Stripe Customer Portal for managing subscription."""
    if not tenant.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No active subscription")

    session = stripe.billing_portal.Session.create(
        customer=tenant.stripe_customer_id,
        return_url="https://cortaloom.ai/billing",
    )
    return {"portal_url": session.url}


# --- Usage Metering ---


async def record_extraction_usage(db: AsyncSession, tenant: Organization) -> bool:
    """Increment extraction count, check budget cap, report overage, send alerts.

    Returns True if the extraction is allowed, False if budget cap reached.
    """
    from datetime import datetime, timezone

    from app.core.audit import log_event

    now = datetime.now(timezone.utc)

    # Reset counter + alert flags if new billing cycle
    if tenant.billing_cycle_start:
        days_since = (now - tenant.billing_cycle_start).days
        if days_since >= 30:
            tenant.monthly_extraction_count = 0
            tenant.billing_cycle_start = now
            tenant.alert_at_80_sent = False
            tenant.alert_at_100_sent = False
    else:
        tenant.billing_cycle_start = now

    tier_config = TIERS.get(tenant.subscription_tier or "", {})
    included = tier_config.get("included_extractions", 0)
    current_count = (tenant.monthly_extraction_count or 0) + 1
    overage = max(0, current_count - included)
    overage_cost = overage * 2.50

    # Budget cap enforcement — block extraction if cap reached
    if tenant.overage_budget_cap is not None and overage_cost > tenant.overage_budget_cap:
        logger.warning(
            "Budget cap reached for %s: overage $%.2f > cap $%.2f",
            tenant.name, overage_cost, tenant.overage_budget_cap,
        )
        await log_event(
            db, "budget_cap_reached", "organization", tenant.id,
            metadata={"overage_cost": overage_cost, "budget_cap": tenant.overage_budget_cap},
        )
        await db.commit()
        return False

    # Allow extraction
    tenant.monthly_extraction_count = current_count
    await db.commit()

    # --- Threshold alerts ---
    usage_pct = (current_count / included * 100) if included > 0 else 100

    # 80% alert
    if usage_pct >= 80 and not tenant.alert_at_80_sent:
        tenant.alert_at_80_sent = True
        await db.commit()
        await log_event(
            db, "usage_alert_80pct", "organization", tenant.id,
            metadata={"usage_pct": round(usage_pct, 1), "count": current_count, "limit": included},
        )
        logger.info("ALERT: %s at %.0f%% of extraction limit (%d/%d)",
                     tenant.name, usage_pct, current_count, included)

    # 100% alert
    if usage_pct >= 100 and not tenant.alert_at_100_sent:
        tenant.alert_at_100_sent = True
        await db.commit()
        await log_event(
            db, "usage_alert_100pct", "organization", tenant.id,
            metadata={"usage_pct": round(usage_pct, 1), "count": current_count, "limit": included},
        )
        logger.info("ALERT: %s has reached extraction limit (%d/%d) — overages begin",
                     tenant.name, current_count, included)

    # Report overage to Stripe meter
    if current_count > included and tenant.stripe_customer_id:
        try:
            stripe.billing.MeterEvent.create(
                event_name=STRIPE_METER_EVENT_NAME,
                payload={
                    "value": "1",
                    "stripe_customer_id": tenant.stripe_customer_id,
                },
            )
            logger.info(
                "Reported overage extraction to Stripe for %s (count=%d, limit=%d)",
                tenant.name, current_count, included,
            )
        except Exception as e:
            logger.error("Failed to report Stripe meter event: %s", str(e))

    return True


# --- Webhook ---


async def handle_stripe_webhook(request: Request, db: AsyncSession):
    """Process Stripe webhook events to update subscription status and tier."""
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    webhook_secret = settings.stripe_webhook_secret.get_secret_value()

    if webhook_secret:
        try:
            event = stripe.Webhook.construct_event(payload, sig, webhook_secret)
        except stripe.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
    else:
        import json as json_mod
        event = stripe.Event.construct_from(json_mod.loads(payload), stripe.api_key)

    event_type = event.type
    data = event.data.object

    if event_type in (
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    ):
        customer_id = data.get("customer")
        status = data.get("status")

        # Extract tier from subscription metadata or items
        tier = data.get("metadata", {}).get("tier")
        if not tier:
            # Try to detect tier from price
            for item in data.get("items", {}).get("data", []):
                price_id = item.get("price", {}).get("id")
                for t_id, t_config in TIERS.items():
                    if t_config["price_id"] == price_id:
                        tier = t_id
                        break

        result = await db.execute(
            select(Organization).where(Organization.stripe_customer_id == customer_id)
        )
        org = result.scalar_one_or_none()
        if org:
            org.subscription_status = status
            if tier:
                org.subscription_tier = tier
            await db.commit()
            logger.info("Updated subscription for %s: status=%s tier=%s", org.name, status, tier)

    return JSONResponse({"status": "ok"})
