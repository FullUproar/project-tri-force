"""Case management endpoints — group documents into a case with a human-readable ID."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_event
from app.core.security import get_current_tenant
from app.dependencies import get_db
from app.models.database import Case, IngestionJob, Organization, generate_short_id
from app.models.schemas import CaseResponse, CreateCaseRequest

router = APIRouter()

MAX_SHORT_ID_ATTEMPTS = 10


async def _generate_unique_short_id(db: AsyncSession, tenant_id: uuid.UUID) -> str:
    """Generate a short ID unique within the tenant, retrying on collision."""
    for _ in range(MAX_SHORT_ID_ATTEMPTS):
        short_id = generate_short_id()
        existing = await db.execute(
            select(Case)
            .where(Case.tenant_id == tenant_id)
            .where(Case.short_id == short_id)
            .limit(1)
        )
        if not existing.scalar_one_or_none():
            return short_id
    # Extremely unlikely — fall back to 6-char ID
    return generate_short_id(length=6)


@router.post("/cases", response_model=CaseResponse)
async def create_case(
    body: CreateCaseRequest | None = None,
    db: AsyncSession = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
):
    """Create a new case with a human-readable short ID."""
    short_id = await _generate_unique_short_id(db, tenant.id)

    case = Case(
        tenant_id=tenant.id,
        short_id=short_id,
        label=body.label if body else None,
    )
    db.add(case)
    await db.commit()
    await db.refresh(case)

    await log_event(
        db, "create_case", "case", case.id,
        metadata={"short_id": short_id, "label": case.label},
        tenant_id=tenant.id,
    )
    await db.commit()

    return CaseResponse(
        id=case.id,
        short_id=case.short_id,
        label=case.label,
        status=case.status,
        created_at=case.created_at,
        document_count=0,
    )


@router.get("/cases", response_model=list[CaseResponse])
async def list_cases(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
):
    """List cases for the current tenant, most recent first."""
    doc_counts = (
        select(
            IngestionJob.case_id,
            func.count().label("doc_count"),
        )
        .where(IngestionJob.case_id.isnot(None))
        .group_by(IngestionJob.case_id)
        .subquery()
    )

    query = (
        select(
            Case,
            func.coalesce(doc_counts.c.doc_count, 0).label("doc_count"),
        )
        .outerjoin(doc_counts, Case.id == doc_counts.c.case_id)
        .where(Case.tenant_id == tenant.id)
    )
    if status:
        query = query.where(Case.status == status)
    query = query.order_by(Case.created_at.desc()).limit(limit).offset(offset)

    rows = await db.execute(query)
    return [
        CaseResponse(
            id=case.id,
            short_id=case.short_id,
            label=case.label,
            status=case.status,
            denial_reason=case.denial_reason,
            created_at=case.created_at,
            document_count=dc,
        )
        for case, dc in rows.all()
    ]


@router.get("/cases/{short_id}", response_model=CaseResponse)
async def get_case(
    short_id: str,
    db: AsyncSession = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
):
    """Get a case by its short ID."""
    result = await db.execute(
        select(Case)
        .where(Case.tenant_id == tenant.id)
        .where(Case.short_id == short_id.upper())
        .limit(1)
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Count documents
    doc_count_result = await db.execute(
        select(func.count()).select_from(IngestionJob).where(IngestionJob.case_id == case.id)
    )
    doc_count = doc_count_result.scalar() or 0

    return CaseResponse(
        id=case.id,
        short_id=case.short_id,
        label=case.label,
        status=case.status,
        denial_reason=case.denial_reason,
        created_at=case.created_at,
        document_count=doc_count,
    )


@router.patch("/cases/{short_id}")
async def update_case(
    short_id: str,
    label: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
):
    """Update case label or status."""
    result = await db.execute(
        select(Case)
        .where(Case.tenant_id == tenant.id)
        .where(Case.short_id == short_id.upper())
        .limit(1)
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    valid_statuses = {"open", "submitted", "approved", "denied", "appealed"}
    if status and status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Status must be one of: {valid_statuses}")

    if label is not None:
        case.label = label
    if status:
        case.status = status

    await db.commit()
    return {"status": "ok", "short_id": case.short_id}
