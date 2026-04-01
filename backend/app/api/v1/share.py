"""Read-only share links for completed prior authorizations."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_db
from app.models.database import ExtractionResult, PayerNarrative

router = APIRouter()


@router.get("/share/{extraction_id}")
async def get_shared_prior_auth(
    extraction_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Public read-only view of a completed prior authorization.

    No API key required — the extraction UUID acts as a capability token.
    UUIDs are unguessable (122 bits of entropy).
    """
    result = await db.execute(
        select(ExtractionResult)
        .options(selectinload(ExtractionResult.ingestion_job))
        .where(ExtractionResult.id == extraction_id)
    )
    ext = result.scalar_one_or_none()
    if not ext:
        raise HTTPException(status_code=404, detail="Prior authorization not found")

    # Get the latest narrative
    narrative_result = await db.execute(
        select(PayerNarrative)
        .where(PayerNarrative.extraction_result_id == extraction_id)
        .order_by(PayerNarrative.created_at.desc())
        .limit(1)
    )
    narrative = narrative_result.scalar_one_or_none()

    return {
        "diagnosis_code": ext.diagnosis_code,
        "conservative_treatments_failed": ext.conservative_treatments_failed,
        "implant_type_requested": ext.implant_type_requested,
        "robotic_assistance_required": ext.robotic_assistance_required,
        "clinical_justification": ext.clinical_justification,
        "confidence_score": ext.confidence_score,
        "outcome": ext.outcome,
        "narrative": narrative.narrative_text if narrative else None,
        "created_at": ext.created_at.isoformat() if ext.created_at else None,
    }
