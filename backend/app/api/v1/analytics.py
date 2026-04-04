"""Analytics endpoints for payer outcome tracking and usage metrics."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_tenant
from app.dependencies import get_db
from app.models.database import ExtractionResult, IngestionJob, Organization

router = APIRouter()


@router.get("/analytics/outcomes")
async def get_outcome_stats(
    db: AsyncSession = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
):
    """Aggregate outcome statistics for the current tenant."""
    result = await db.execute(
        select(
            ExtractionResult.outcome,
            func.count().label("count"),
        )
        .where(ExtractionResult.tenant_id == tenant.id)
        .where(ExtractionResult.outcome.is_not(None))
        .group_by(ExtractionResult.outcome)
    )
    rows = result.all()

    stats = {row.outcome: row.count for row in rows}
    total = sum(stats.values())

    return {
        "total_with_outcome": total,
        "approved": stats.get("approved", 0),
        "denied": stats.get("denied", 0),
        "pending": stats.get("pending", 0),
        "appealed": stats.get("appealed", 0),
        "approval_rate": round(stats.get("approved", 0) / total * 100, 1) if total > 0 else None,
    }


@router.get("/analytics/usage")
async def get_usage_stats(
    db: AsyncSession = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
):
    """Usage statistics for the current tenant."""
    job_count_result = await db.execute(
        select(func.count()).select_from(IngestionJob).where(IngestionJob.tenant_id == tenant.id)
    )
    total_jobs = job_count_result.scalar() or 0

    extraction_count_result = await db.execute(
        select(func.count()).select_from(ExtractionResult).where(ExtractionResult.tenant_id == tenant.id)
    )
    total_extractions = extraction_count_result.scalar() or 0

    # Average confidence
    avg_confidence_result = await db.execute(
        select(func.avg(ExtractionResult.confidence_score))
        .where(ExtractionResult.tenant_id == tenant.id)
        .where(ExtractionResult.confidence_score.is_not(None))
    )

    return {
        "total_jobs": total_jobs,
        "total_extractions": total_extractions,
        "avg_confidence": round(avg_confidence_result.scalar() or 0, 2),
        "estimated_time_saved_minutes": total_extractions * 44,
    }


@router.get("/analytics/outcomes-by-diagnosis")
async def get_outcomes_by_diagnosis(
    db: AsyncSession = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
):
    """Outcome rates grouped by ICD-10 diagnosis code — the flywheel data."""
    result = await db.execute(
        select(
            ExtractionResult.diagnosis_code,
            ExtractionResult.outcome,
            func.count().label("count"),
        )
        .where(ExtractionResult.tenant_id == tenant.id)
        .where(ExtractionResult.outcome.is_not(None))
        .where(ExtractionResult.diagnosis_code.is_not(None))
        .group_by(ExtractionResult.diagnosis_code, ExtractionResult.outcome)
    )
    rows = result.all()

    # Pivot into {diagnosis: {approved: N, denied: N, ...}}
    data: dict = {}
    for row in rows:
        dx = row.diagnosis_code
        if dx not in data:
            data[dx] = {"diagnosis_code": dx, "approved": 0, "denied": 0, "pending": 0, "appealed": 0, "total": 0}
        data[dx][row.outcome] = row.count
        data[dx]["total"] += row.count

    # Calculate approval rates
    for dx_data in data.values():
        total = dx_data["total"]
        dx_data["approval_rate"] = round(dx_data["approved"] / total * 100, 1) if total > 0 else None

    return sorted(data.values(), key=lambda x: x["total"], reverse=True)


@router.get("/analytics/overrides")
async def get_override_stats(
    db: AsyncSession = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
):
    """Count of user overrides — measures AI accuracy vs. human corrections."""
    from app.models.database import AuditLog

    result = await db.execute(
        select(func.count())
        .select_from(AuditLog)
        .where(AuditLog.tenant_id == tenant.id)
        .where(AuditLog.action == "user_override")
    )
    override_count = result.scalar() or 0

    total_extractions = await db.execute(
        select(func.count())
        .select_from(ExtractionResult)
        .where(ExtractionResult.tenant_id == tenant.id)
    )
    total = total_extractions.scalar() or 0

    return {
        "total_overrides": override_count,
        "total_extractions": total,
        "override_rate": round(override_count / total * 100, 1) if total > 0 else 0,
        "ai_accuracy_proxy": round((1 - override_count / total) * 100, 1) if total > 0 else 100,
    }
