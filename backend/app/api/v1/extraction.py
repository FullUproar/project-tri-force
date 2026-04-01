import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.database import ExtractionResult, PayerNarrative
from app.models.schemas import NarrativeResponse, OrthoPriorAuthData
from app.services.llm.narrative import generate_narrative

router = APIRouter()


@router.post("/extraction/{extraction_id}/narrative", response_model=NarrativeResponse)
async def create_narrative(
    extraction_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Generate a payer submission narrative from an extraction result."""
    ext = await db.get(ExtractionResult, extraction_id)
    if not ext:
        raise HTTPException(status_code=404, detail="Extraction result not found")

    # Reconstruct OrthoPriorAuthData from DB record
    extraction_data = OrthoPriorAuthData(
        diagnosis_code=ext.diagnosis_code or "Not found",
        conservative_treatments_failed=ext.conservative_treatments_failed or [],
        implant_type_requested=ext.implant_type_requested or "Not specified",
        robotic_assistance_required=ext.robotic_assistance_required or False,
        clinical_justification=ext.clinical_justification or "",
        confidence_score=ext.confidence_score or 0.0,
    )

    # Get DICOM metadata if available (from the parent ingestion job)
    additional_context = ""
    job = ext.ingestion_job
    if job and job.metadata_json:
        additional_context = f"Imaging metadata: {job.metadata_json}"

    narrative_text, model_used, prompt_version = await generate_narrative(
        extraction_data, additional_context
    )

    narrative = PayerNarrative(
        extraction_result_id=extraction_id,
        narrative_text=narrative_text,
        model_used=model_used,
        prompt_version=prompt_version,
    )
    db.add(narrative)
    await db.commit()
    await db.refresh(narrative)

    return NarrativeResponse(
        narrative_id=narrative.id,
        narrative_text=narrative_text,
        model_used=model_used,
        prompt_version=prompt_version,
    )
