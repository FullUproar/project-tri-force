"""Admin endpoints for managing organizations and API keys.

These endpoints are protected by the standard API key auth.
In production, add an additional admin role check.
"""

import hashlib
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_tenant, hash_api_key
from app.dependencies import get_db
from app.models.database import ApiKey, ExtractionResult, IngestionJob, Organization

router = APIRouter()


class CreateOrgRequest(BaseModel):
    name: str


class CreateOrgResponse(BaseModel):
    organization_id: str
    name: str
    api_key: str  # Raw key — only shown once


class OrgSummary(BaseModel):
    id: str
    name: str
    is_active: bool
    baa_signed_at: str | None
    job_count: int
    extraction_count: int


@router.post("/admin/organizations", response_model=CreateOrgResponse)
async def create_organization(
    body: CreateOrgRequest,
    db: AsyncSession = Depends(get_db),
    _tenant: Organization = Depends(get_current_tenant),
):
    """Create a new ASC organization with an API key."""
    org = Organization(name=body.name)
    db.add(org)
    await db.flush()

    # Generate a secure API key
    raw_key = f"cl_{secrets.token_urlsafe(32)}"
    key = ApiKey(
        organization_id=org.id,
        key_hash=hash_api_key(raw_key),
        name=f"{body.name} Production Key",
    )
    db.add(key)
    await db.commit()

    return CreateOrgResponse(
        organization_id=str(org.id),
        name=org.name,
        api_key=raw_key,
    )


@router.get("/admin/organizations")
async def list_organizations(
    db: AsyncSession = Depends(get_db),
    _tenant: Organization = Depends(get_current_tenant),
):
    """List all organizations with usage stats."""
    orgs = await db.execute(select(Organization).order_by(Organization.created_at.desc()))
    results = []

    for org in orgs.scalars().all():
        job_count = await db.execute(
            select(func.count()).select_from(IngestionJob).where(IngestionJob.tenant_id == org.id)
        )
        extraction_count = await db.execute(
            select(func.count()).select_from(ExtractionResult).where(ExtractionResult.tenant_id == org.id)
        )

        results.append(OrgSummary(
            id=str(org.id),
            name=org.name,
            is_active=org.is_active,
            baa_signed_at=org.baa_signed_at.isoformat() if org.baa_signed_at else None,
            job_count=job_count.scalar() or 0,
            extraction_count=extraction_count.scalar() or 0,
        ))

    return results


@router.post("/admin/organizations/{org_id}/sign-baa")
async def sign_baa(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _tenant: Organization = Depends(get_current_tenant),
):
    """Mark an organization's BAA as signed."""
    from datetime import datetime, timezone

    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    org.baa_signed_at = datetime.now(timezone.utc)
    await db.commit()

    return {"status": "ok", "organization_id": str(org_id), "baa_signed_at": org.baa_signed_at.isoformat()}
