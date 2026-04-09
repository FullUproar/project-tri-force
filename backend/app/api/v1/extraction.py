import uuid
from datetime import datetime, timezone
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy.ext.asyncio import AsyncSession

from pydantic import BaseModel

from app.core.security import get_current_tenant
from app.dependencies import get_db
from app.models.database import ExtractionResult, Organization, PayerNarrative
from app.models.schemas import NarrativeResponse, OrthoPriorAuthData
from app.services.llm.narrative import generate_narrative

router = APIRouter()


@router.get("/disclosure")
async def get_ai_disclosure():
    """Return the AI disclosure text for TRAIGA compliance."""
    from app.services.llm.prompts import AI_DISCLOSURE_TEXT

    return {"disclosure": AI_DISCLOSURE_TEXT}


class OverrideFieldsRequest(BaseModel):
    diagnosis_code: str | None = None
    conservative_treatments_failed: list[str] | None = None
    implant_type_requested: str | None = None
    robotic_assistance_required: bool | None = None
    clinical_justification: str | None = None


@router.patch("/extraction/{extraction_id}")
async def override_extraction_fields(
    extraction_id: uuid.UUID,
    body: OverrideFieldsRequest,
    db: AsyncSession = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
):
    """Save user overrides to extraction fields and log what changed (QA audit trail)."""
    ext = await db.get(ExtractionResult, extraction_id)
    if not ext or ext.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Extraction result not found")

    changes = {}
    for field_name, new_value in body.model_dump(exclude_none=True).items():
        old_value = getattr(ext, field_name)
        if old_value != new_value:
            changes[field_name] = {"old": old_value, "new": new_value}
            setattr(ext, field_name, new_value)

    if changes:
        from app.core.audit import log_event

        await log_event(
            db, "user_override", "extraction_result", extraction_id,
            metadata={"fields_changed": list(changes.keys()), "changes": changes},
            tenant_id=tenant.id,
        )
        await db.commit()

    return {
        "status": "ok",
        "extraction_id": str(extraction_id),
        "fields_overridden": list(changes.keys()),
    }


@router.post("/extraction/{extraction_id}/narrative", response_model=NarrativeResponse)
async def create_narrative(
    extraction_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
):
    """Generate a payer submission narrative from an extraction result."""
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(ExtractionResult)
        .options(selectinload(ExtractionResult.ingestion_job))
        .where(ExtractionResult.id == extraction_id)
        .where(ExtractionResult.tenant_id == tenant.id)
    )
    ext = result.scalar_one_or_none()
    if not ext:
        raise HTTPException(status_code=404, detail="Extraction result not found")

    extraction_data = OrthoPriorAuthData(
        diagnosis_code=ext.diagnosis_code or "Not found",
        conservative_treatments_failed=ext.conservative_treatments_failed or [],
        implant_type_requested=ext.implant_type_requested or "Not specified",
        robotic_assistance_required=ext.robotic_assistance_required or False,
        clinical_justification=ext.clinical_justification or "",
        confidence_score=ext.confidence_score or 0.0,
    )

    additional_context = ""
    if ext.ingestion_job and ext.ingestion_job.metadata_json:
        additional_context = f"Imaging metadata: {ext.ingestion_job.metadata_json}"

    narrative_text, model_used, prompt_version = await generate_narrative(
        extraction_data, additional_context
    )

    narrative = PayerNarrative(
        tenant_id=tenant.id,
        extraction_result_id=extraction_id,
        narrative_text=narrative_text,
        model_used=model_used,
        prompt_version=prompt_version,
    )
    db.add(narrative)
    await db.commit()
    await db.refresh(narrative)

    from app.core.audit import log_event

    await log_event(
        db, "narrative", "payer_narrative", narrative.id,
        metadata={"extraction_id": str(extraction_id), "model": model_used, "prompt_version": prompt_version},
        tenant_id=tenant.id,
    )
    await db.commit()

    return NarrativeResponse(
        narrative_id=narrative.id,
        narrative_text=narrative_text,
        model_used=model_used,
        prompt_version=prompt_version,
    )


class UpdateOutcomeRequest(BaseModel):
    outcome: str  # approved, denied, pending, appealed


@router.patch("/extraction/{extraction_id}/outcome")
async def update_outcome(
    extraction_id: uuid.UUID,
    body: UpdateOutcomeRequest,
    db: AsyncSession = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
):
    """Update the prior auth outcome for tracking."""
    valid_outcomes = {"approved", "denied", "pending", "appealed"}
    if body.outcome not in valid_outcomes:
        raise HTTPException(status_code=400, detail=f"Outcome must be one of: {valid_outcomes}")

    ext = await db.get(ExtractionResult, extraction_id)
    if not ext or ext.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Extraction result not found")

    ext.outcome = body.outcome
    await db.commit()
    return {"status": "ok", "extraction_id": str(extraction_id), "outcome": body.outcome}


@router.get("/extraction/{extraction_id}/export/pdf")
async def export_pdf(
    extraction_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
):
    """Export the prior authorization as a formatted PDF."""
    ext = await db.get(ExtractionResult, extraction_id)
    if not ext or ext.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Extraction result not found")

    # Find the most recent narrative for this extraction
    from sqlalchemy import select

    result = await db.execute(
        select(PayerNarrative)
        .where(PayerNarrative.extraction_result_id == extraction_id)
        .order_by(PayerNarrative.created_at.desc())
        .limit(1)
    )
    narrative = result.scalar_one_or_none()

    # Build PDF
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    styles = getSampleStyleSheet()

    header_style = ParagraphStyle("Header", parent=styles["Heading1"], fontSize=16, spaceAfter=6)
    sub_style = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=9, textColor="#666666")
    section_style = ParagraphStyle("Section", parent=styles["Heading2"], fontSize=12, spaceAfter=4)
    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, leading=14)
    footer_style = ParagraphStyle(
        "Footer", parent=styles["Normal"], fontSize=8, textColor="#999999", alignment=1
    )

    elements = []

    # Header with case metadata
    elements.append(Paragraph("CortaLoom — Prior Authorization Request", header_style))
    meta_parts = [
        f"Generated: {datetime.now(timezone.utc).strftime('%B %d, %Y')}",
        f"Case Ref: {str(extraction_id)[:8]}",
    ]
    if ext.diagnosis_code:
        meta_parts.append(f"Dx: {ext.diagnosis_code}")
    if ext.outcome:
        meta_parts.append(f"Outcome: {ext.outcome.capitalize()}")
    elements.append(Paragraph(" | ".join(meta_parts), sub_style))
    elements.append(Spacer(1, 0.3 * inch))

    # Extracted Fields
    elements.append(Paragraph("Clinical Summary", section_style))
    fields = [
        f"<b>Diagnosis Code:</b> {ext.diagnosis_code or 'N/A'}",
        f"<b>Implant Requested:</b> {ext.implant_type_requested or 'N/A'}",
        f"<b>Robotic Assistance:</b> {'Yes' if ext.robotic_assistance_required else 'No'}",
        f"<b>Conservative Treatments Failed:</b> {', '.join(ext.conservative_treatments_failed or [])}",
    ]
    for field in fields:
        elements.append(Paragraph(field, body_style))
        elements.append(Spacer(1, 4))

    if ext.clinical_justification:
        elements.append(Spacer(1, 0.15 * inch))
        elements.append(Paragraph("<b>Clinical Justification:</b>", body_style))
        elements.append(Paragraph(ext.clinical_justification, body_style))

    # Narrative
    if narrative:
        elements.append(Spacer(1, 0.3 * inch))
        elements.append(Paragraph("Payer Submission Narrative", section_style))
        elements.append(Paragraph(narrative.narrative_text, body_style))

    # AI Disclosure (Texas TRAIGA compliance)
    from app.services.llm.prompts import AI_DISCLOSURE_TEXT

    disclosure_style = ParagraphStyle(
        "Disclosure", parent=styles["Normal"], fontSize=7, textColor="#888888",
        leading=10, spaceBefore=12, borderWidth=0.5, borderColor="#cccccc",
        borderPadding=6,
    )
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph(f"<b>AI Disclosure:</b> {AI_DISCLOSURE_TEXT}", disclosure_style))

    # Footer
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(
        Paragraph(
            "Generated by CortaLoom AI — For clinical review before submission",
            footer_style,
        )
    )

    doc.build(elements)
    buf.seek(0)

    filename = f"prior-auth-{str(extraction_id)[:8]}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
