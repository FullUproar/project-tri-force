"""Payer policy intelligence endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_tenant
from app.dependencies import get_db
from app.models.database import Organization, PayerPolicy

router = APIRouter()


@router.get("/policies")
async def list_policies(
    payer: str | None = Query(None, description="Filter by payer name"),
    procedure: str | None = Query(None, description="Filter by procedure"),
    db: AsyncSession = Depends(get_db),
    _tenant: Organization = Depends(get_current_tenant),
):
    """List payer policies with optional filters."""
    query = select(PayerPolicy).where(PayerPolicy.status == "active")
    if payer:
        query = query.where(PayerPolicy.payer == payer)
    if procedure:
        query = query.where(PayerPolicy.procedure == procedure)
    query = query.order_by(PayerPolicy.payer, PayerPolicy.procedure)

    result = await db.execute(query)
    policies = result.scalars().all()

    return [
        {
            "id": str(p.id),
            "payer": p.payer,
            "procedure": p.procedure,
            "criteria": p.criteria,
            "source_url": p.source_url,
            "version": p.version,
            "verified_date": p.verified_date.isoformat() if p.verified_date else None,
            "status": p.status,
        }
        for p in policies
    ]


@router.get("/policies/payers")
async def list_payers(
    db: AsyncSession = Depends(get_db),
    _tenant: Organization = Depends(get_current_tenant),
):
    """List distinct payer names."""
    from sqlalchemy import distinct

    result = await db.execute(
        select(distinct(PayerPolicy.payer)).where(PayerPolicy.status == "active")
    )
    return [row[0] for row in result.all()]


@router.get("/policies/procedures")
async def list_procedures(
    payer: str | None = Query(None, description="Filter procedures by payer"),
    db: AsyncSession = Depends(get_db),
    _tenant: Organization = Depends(get_current_tenant),
):
    """List distinct procedure names, optionally filtered by payer."""
    from sqlalchemy import distinct

    query = select(distinct(PayerPolicy.procedure)).where(PayerPolicy.status == "active")
    if payer:
        query = query.where(PayerPolicy.payer == payer)
    result = await db.execute(query)
    return [row[0] for row in result.all()]


@router.get("/policies/suggest-procedure")
async def suggest_procedure(
    diagnosis_code: str = Query(..., description="ICD-10 diagnosis code"),
    _tenant: Organization = Depends(get_current_tenant),
):
    """Suggest a procedure based on ICD-10 code for payer policy lookup."""
    from app.services.llm.prompts import suggest_procedure_from_diagnosis

    procedure = suggest_procedure_from_diagnosis(diagnosis_code)
    return {"diagnosis_code": diagnosis_code, "suggested_procedure": procedure}


@router.get("/policies/check")
async def check_readiness_against_policy(
    payer: str = Query(..., description="Payer name (UHC, Aetna, BCBS, Cigna, Humana)"),
    procedure: str = Query(..., description="Procedure name"),
    treatments_count: int = Query(0),
    has_imaging: bool = Query(False),
    symptom_months: int = Query(0),
    db: AsyncSession = Depends(get_db),
    _tenant: Organization = Depends(get_current_tenant),
):
    """Check extraction data against a specific payer's policy criteria."""
    result = await db.execute(
        select(PayerPolicy)
        .where(PayerPolicy.payer == payer)
        .where(PayerPolicy.procedure == procedure)
        .where(PayerPolicy.status == "active")
        .limit(1)
    )
    policy = result.scalar_one_or_none()

    if not policy:
        return {"match": False, "message": f"No policy found for {payer} / {procedure}"}

    criteria = policy.criteria
    gaps = []

    # Check conservative treatment duration
    min_months = criteria.get("conservative_treatment_min_months", 0)
    if symptom_months < min_months:
        gaps.append(f"{payer} requires {min_months}+ months of conservative treatment")

    # Check treatment modalities
    required = criteria.get("required_modalities", [])
    if treatments_count < len(required):
        gaps.append(f"{payer} requires {len(required)} treatment modalities: {', '.join(required)}")

    # Check imaging
    if criteria.get("imaging_required") and not has_imaging:
        gaps.append(f"{payer} requires: {criteria['imaging_required']}")

    # Check trial requirement (SCS)
    if criteria.get("trial_required"):
        gaps.append(f"{payer} requires a successful trial before permanent implant")

    score = max(0, 100 - (len(gaps) * 25))

    return {
        "payer": payer,
        "procedure": procedure,
        "policy_version": policy.version,
        "readiness_score": score,
        "gaps": gaps,
        "submission_portal": criteria.get("submission_portal", "Unknown"),
        "criteria": criteria,
    }
