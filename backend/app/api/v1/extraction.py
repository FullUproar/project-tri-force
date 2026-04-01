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
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(ExtractionResult)
        .options(selectinload(ExtractionResult.ingestion_job))
        .where(ExtractionResult.id == extraction_id)
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
    )
    await db.commit()

    return NarrativeResponse(
        narrative_id=narrative.id,
        narrative_text=narrative_text,
        model_used=model_used,
        prompt_version=prompt_version,
    )


@router.get("/extraction/{extraction_id}/export/pdf")
async def export_pdf(
    extraction_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Export the prior authorization as a formatted PDF."""
    ext = await db.get(ExtractionResult, extraction_id)
    if not ext:
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

    # Header
    elements.append(Paragraph("CortaLoom — Prior Authorization", header_style))
    elements.append(
        Paragraph(
            f"Generated: {datetime.now(timezone.utc).strftime('%B %d, %Y')} | "
            f"Case Ref: {str(extraction_id)[:8]}",
            sub_style,
        )
    )
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

    # Footer
    elements.append(Spacer(1, 0.5 * inch))
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
