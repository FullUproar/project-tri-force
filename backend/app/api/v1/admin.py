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

from app.core.security import get_admin_tenant, get_current_tenant, hash_api_key
from app.dependencies import get_db
from app.models.database import ApiKey, ExtractionResult, IngestionJob, Organization

import json
from pathlib import Path

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


@router.get("/me")
async def get_current_org(
    tenant: Organization = Depends(get_current_tenant),
):
    """Return the current tenant's organization info and role."""
    return {
        "id": str(tenant.id),
        "name": tenant.name,
        "is_admin": tenant.is_admin,
        "subscription_tier": tenant.subscription_tier,
        "subscription_status": tenant.subscription_status,
        "verticals": tenant.verticals,
        "baa_signed_at": tenant.baa_signed_at.isoformat() if tenant.baa_signed_at else None,
    }


@router.post("/admin/organizations", response_model=CreateOrgResponse)
async def create_organization(
    body: CreateOrgRequest,
    db: AsyncSession = Depends(get_db),
    _tenant: Organization = Depends(get_admin_tenant),
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
    _tenant: Organization = Depends(get_admin_tenant),
):
    """List all organizations with usage stats (single query, no N+1)."""
    job_counts = (
        select(
            IngestionJob.tenant_id,
            func.count().label("job_count"),
        )
        .group_by(IngestionJob.tenant_id)
        .subquery()
    )
    extraction_counts = (
        select(
            ExtractionResult.tenant_id,
            func.count().label("extraction_count"),
        )
        .group_by(ExtractionResult.tenant_id)
        .subquery()
    )

    query = (
        select(
            Organization,
            func.coalesce(job_counts.c.job_count, 0).label("job_count"),
            func.coalesce(extraction_counts.c.extraction_count, 0).label("extraction_count"),
        )
        .outerjoin(job_counts, Organization.id == job_counts.c.tenant_id)
        .outerjoin(extraction_counts, Organization.id == extraction_counts.c.tenant_id)
        .order_by(Organization.created_at.desc())
    )

    rows = await db.execute(query)
    return [
        OrgSummary(
            id=str(org.id),
            name=org.name,
            is_active=org.is_active,
            baa_signed_at=org.baa_signed_at.isoformat() if org.baa_signed_at else None,
            job_count=jc,
            extraction_count=ec,
        )
        for org, jc, ec in rows.all()
    ]


@router.post("/admin/organizations/{org_id}/sign-baa")
async def sign_baa(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _tenant: Organization = Depends(get_admin_tenant),
):
    """Mark an organization's BAA as signed."""
    from datetime import datetime, timezone

    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    org.baa_signed_at = datetime.now(timezone.utc)
    await db.commit()

    return {"status": "ok", "organization_id": str(org_id), "baa_signed_at": org.baa_signed_at.isoformat()}


@router.post("/admin/load-demo-data")
async def load_demo_data(
    db: AsyncSession = Depends(get_db),
    tenant: Organization = Depends(get_admin_tenant),
):
    """Load synthetic demo cases into the current tenant's data."""
    demo_file = Path(__file__).parent.parent.parent.parent / "docs" / "synthetic-demo-data.json"
    if not demo_file.exists():
        raise HTTPException(status_code=404, detail="Demo data file not found")

    with open(demo_file) as f:
        cases = json.load(f)

    loaded = 0
    for case in cases:
        job = IngestionJob(
            tenant_id=tenant.id,
            source_type="clinical_note",
            status="completed",
            original_filename=f"demo-{case['patient_id']}.txt",
            file_size_bytes=len(case.get("clinical_notes_text", "")),
        )
        db.add(job)
        await db.flush()

        ext = ExtractionResult(
            tenant_id=tenant.id,
            ingestion_job_id=job.id,
            diagnosis_code=case.get("diagnosis_code"),
            conservative_treatments_failed=case.get("conservative_treatments_failed", []),
            implant_type_requested=case.get("device_requested", case.get("implant_type_requested", "Not specified")),
            robotic_assistance_required=False,
            clinical_justification=case.get("functional_impairment", ""),
            confidence_score=0.95,
            raw_extraction_json=case,
            schema_version="ortho_v1" if case.get("case_type") in ("hip_replacement", "knee_arthroscopy", "rotator_cuff_repair") else "spine_v1",
        )
        db.add(ext)
        loaded += 1

    await db.commit()
    return {"status": "ok", "cases_loaded": loaded}
