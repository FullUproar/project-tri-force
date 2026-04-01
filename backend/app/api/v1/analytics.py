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
    job_count = await db.execute(
        select(func.count()).select_from(IngestionJob).where(IngestionJob.tenant_id == tenant.id)
    )
    extraction_count = await db.execute(
        select(func.count()).select_from(ExtractionResult).where(ExtractionResult.tenant_id == tenant.id)
    )

    # Average confidence
    avg_confidence = await db.execute(
        select(func.avg(ExtractionResult.confidence_score))
        .where(ExtractionResult.tenant_id == tenant.id)
        .where(ExtractionResult.confidence_score.is_not(None))
    )

    return {
        "total_jobs": job_count.scalar() or 0,
        "total_extractions": extraction_count.scalar() or 0,
        "avg_confidence": round(avg_confidence.scalar() or 0, 2),
        "estimated_time_saved_minutes": (extraction_count.scalar() or 0) * 44,
    }
