import uuid
from datetime import datetime, timezone
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy.ext.asyncio import AsyncSession

from pydantic import BaseModel

from app.core.security import get_current_tenant
from app.dependencies import get_db
from app.models.database import ExtractionResult, NarrativeCitation, NarrativeVersion, Organization, PayerNarrative, PayerPolicy, PayerPolicyChunk
from app.models.schemas import (
    DenialReasonRequest,
    EditNarrativeRequest,
    GenerateNarrativeRequest,
    NarrativeResponse,
    NarrativeVersionResponse,
    OrthoPriorAuthData,
)
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
    body: GenerateNarrativeRequest | None = None,
    db: AsyncSession = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
):
    """Generate a payer submission narrative from an extraction result.

    Optionally accepts payer and procedure to generate a payer-specific narrative
    tailored to that insurer's requirements.
    """
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
        procedure_cpt_codes=ext.procedure_cpt_codes or [],
        conservative_treatments_failed=ext.conservative_treatments_failed or [],
        implant_type_requested=ext.implant_type_requested or "Not specified",
        robotic_assistance_required=ext.robotic_assistance_required or False,
        clinical_justification=ext.clinical_justification or "",
        confidence_score=ext.confidence_score or 0.0,
    )

    additional_context = ""
    if ext.ingestion_job and ext.ingestion_job.metadata_json:
        additional_context = f"Imaging metadata: {ext.ingestion_job.metadata_json}"

    # Look up payer-specific criteria and policy chunks for RAG
    payer_name = body.payer if body else None
    procedure_name = body.procedure if body else None
    payer_criteria = None
    policy_chunks = []

    if payer_name:
        # Auto-suggest procedure from diagnosis code if not explicitly provided
        if not procedure_name:
            from app.services.llm.prompts import suggest_procedure_from_diagnosis
            procedure_name = suggest_procedure_from_diagnosis(ext.diagnosis_code)

        if procedure_name:
            policy_result = await db.execute(
                select(PayerPolicy)
                .where(PayerPolicy.payer == payer_name)
                .where(PayerPolicy.procedure == procedure_name)
                .where(PayerPolicy.status == "active")
                .limit(1)
            )
            policy = policy_result.scalar_one_or_none()
            if policy:
                payer_criteria = policy.criteria

            # Retrieve policy chunks for RAG context + citations
            chunks_result = await db.execute(
                select(PayerPolicyChunk)
                .where(PayerPolicyChunk.payer == payer_name)
                .where(PayerPolicyChunk.procedure == procedure_name)
                .order_by(PayerPolicyChunk.chunk_index)
                .limit(10)
            )
            policy_chunks = list(chunks_result.scalars().all())

    narrative_text, model_used, prompt_version, citations_raw = await generate_narrative(
        extraction_data,
        additional_context,
        payer_name=payer_name,
        procedure_name=procedure_name,
        payer_criteria=payer_criteria,
        policy_chunks=policy_chunks if policy_chunks else None,
    )

    narrative = PayerNarrative(
        tenant_id=tenant.id,
        extraction_result_id=extraction_id,
        narrative_text=narrative_text,
        model_used=model_used,
        prompt_version=prompt_version,
        payer=payer_name,
        procedure=procedure_name,
    )
    db.add(narrative)
    await db.commit()
    await db.refresh(narrative)

    # Save version 0 (AI-generated, immutable baseline)
    v0 = NarrativeVersion(
        narrative_id=narrative.id,
        version_number=0,
        narrative_text=narrative_text,
        source="ai",
    )
    db.add(v0)
    await db.commit()

    # Store citations if any were generated
    stored_citations = []
    for cit in citations_raw:
        source_chunk_id = None
        source_text = None
        section_title = None
        source_type = cit.get("source_type", "payer_policy")

        # Map source_index back to the actual chunk
        source_idx = cit.get("source_index")
        if source_idx is not None and isinstance(source_idx, int):
            # Index 0 is clinical data, 1+ are policy chunks
            chunk_offset = source_idx - 1  # subtract 1 for clinical data at index 0
            if chunk_offset >= 0 and chunk_offset < len(policy_chunks):
                chunk = policy_chunks[chunk_offset]
                source_chunk_id = chunk.id
                source_text = chunk.content
                section_title = chunk.section_title
                source_type = "payer_policy"
            elif source_idx == 0:
                source_type = "clinical_note"
                source_text = extraction_data.clinical_justification

        citation = NarrativeCitation(
            narrative_id=narrative.id,
            marker=str(cit.get("marker", "")),
            claim_text=cit.get("claim", ""),
            source_type=source_type,
            source_chunk_id=source_chunk_id,
            source_text=source_text,
            section_title=section_title,
        )
        db.add(citation)
        stored_citations.append({
            "marker": citation.marker,
            "claim": citation.claim_text,
            "source_type": citation.source_type,
            "source_text": citation.source_text,
            "section_title": citation.section_title,
        })

    if stored_citations:
        await db.commit()

    from app.core.audit import log_event

    await log_event(
        db, "narrative", "payer_narrative", narrative.id,
        metadata={
            "extraction_id": str(extraction_id),
            "model": model_used,
            "prompt_version": prompt_version,
            "payer": payer_name,
            "procedure": procedure_name,
            "citation_count": len(stored_citations),
        },
        tenant_id=tenant.id,
    )
    await db.commit()

    return NarrativeResponse(
        narrative_id=narrative.id,
        narrative_text=narrative_text,
        model_used=model_used,
        prompt_version=prompt_version,
        payer=payer_name,
        procedure=procedure_name,
        citations=stored_citations if stored_citations else None,
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
        f"<b>CPT Code(s):</b> {', '.join(ext.procedure_cpt_codes) if ext.procedure_cpt_codes else 'N/A'}",
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
    was_edited = False
    if narrative:
        elements.append(Spacer(1, 0.3 * inch))
        elements.append(Paragraph("Payer Submission Narrative", section_style))
        elements.append(Paragraph(narrative.narrative_text, body_style))

        # Check if narrative was human-edited
        version_result = await db.execute(
            select(NarrativeVersion)
            .where(NarrativeVersion.narrative_id == narrative.id)
            .where(NarrativeVersion.source == "human_edit")
            .limit(1)
        )
        was_edited = version_result.scalar_one_or_none() is not None

    # AI Disclosure (Texas TRAIGA compliance) — adaptive based on editing
    from app.services.llm.prompts import AI_DISCLOSURE_TEXT

    if was_edited:
        disclosure_text = (
            "This prior authorization document was prepared with AI assistance using CortaLoom.AI. "
            "AI technology (Anthropic Claude) was used to generate an initial draft narrative, "
            "which was subsequently reviewed and edited by the submitting user. "
            "CortaLoom is an administrative workflow tool and does not provide clinical recommendations."
        )
    else:
        disclosure_text = AI_DISCLOSURE_TEXT

    disclosure_style = ParagraphStyle(
        "Disclosure", parent=styles["Normal"], fontSize=7, textColor="#888888",
        leading=10, spaceBefore=12, borderWidth=0.5, borderColor="#cccccc",
        borderPadding=6,
    )
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph(f"<b>AI Disclosure:</b> {disclosure_text}", disclosure_style))

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


# --- Narrative Editing ---


@router.put("/narrative/{narrative_id}/edit")
async def edit_narrative(
    narrative_id: uuid.UUID,
    body: EditNarrativeRequest,
    db: AsyncSession = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
):
    """Save a human edit to a narrative. Creates a new version snapshot."""
    narrative = await db.get(PayerNarrative, narrative_id)
    if not narrative or narrative.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Narrative not found")

    # Get next version number
    max_version_result = await db.execute(
        select(func.max(NarrativeVersion.version_number))
        .where(NarrativeVersion.narrative_id == narrative_id)
    )
    max_version = max_version_result.scalar() or 0
    next_version = max_version + 1

    # Save version snapshot
    version = NarrativeVersion(
        narrative_id=narrative_id,
        version_number=next_version,
        narrative_text=body.narrative_text,
        source="human_edit",
    )
    db.add(version)

    # Update current narrative text
    narrative.narrative_text = body.narrative_text
    await db.commit()

    from app.core.audit import log_event
    await log_event(
        db, "narrative_edit", "payer_narrative", narrative_id,
        metadata={"version": next_version},
        tenant_id=tenant.id,
    )
    await db.commit()

    return {
        "status": "ok",
        "narrative_id": str(narrative_id),
        "version": next_version,
        "source": "human_edit",
    }


@router.get("/narrative/{narrative_id}/versions", response_model=list[NarrativeVersionResponse])
async def get_narrative_versions(
    narrative_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
):
    """Get the full version history of a narrative."""
    narrative = await db.get(PayerNarrative, narrative_id)
    if not narrative or narrative.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Narrative not found")

    result = await db.execute(
        select(NarrativeVersion)
        .where(NarrativeVersion.narrative_id == narrative_id)
        .order_by(NarrativeVersion.version_number.desc())
    )
    versions = result.scalars().all()

    return [
        NarrativeVersionResponse(
            id=v.id,
            version_number=v.version_number,
            narrative_text=v.narrative_text,
            source=v.source,
            created_at=v.created_at,
        )
        for v in versions
    ]


@router.post("/narrative/{narrative_id}/revert/{version_number}")
async def revert_narrative(
    narrative_id: uuid.UUID,
    version_number: int,
    db: AsyncSession = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
):
    """Revert a narrative to a specific version (creates a new version from the old snapshot)."""
    narrative = await db.get(PayerNarrative, narrative_id)
    if not narrative or narrative.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Narrative not found")

    # Find the target version
    target_result = await db.execute(
        select(NarrativeVersion)
        .where(NarrativeVersion.narrative_id == narrative_id)
        .where(NarrativeVersion.version_number == version_number)
    )
    target = target_result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Version not found")

    # Get next version number
    max_version_result = await db.execute(
        select(func.max(NarrativeVersion.version_number))
        .where(NarrativeVersion.narrative_id == narrative_id)
    )
    max_version = max_version_result.scalar() or 0
    next_version = max_version + 1

    # Create a new version that's a copy of the target
    revert_version = NarrativeVersion(
        narrative_id=narrative_id,
        version_number=next_version,
        narrative_text=target.narrative_text,
        source=f"revert_to_v{version_number}",
    )
    db.add(revert_version)

    # Update current text
    narrative.narrative_text = target.narrative_text
    await db.commit()

    return {
        "status": "ok",
        "narrative_id": str(narrative_id),
        "reverted_to": version_number,
        "new_version": next_version,
    }


# --- Appeal Letter Generation ---


@router.post("/extraction/{extraction_id}/appeal", response_model=NarrativeResponse)
async def generate_appeal(
    extraction_id: uuid.UUID,
    body: DenialReasonRequest,
    db: AsyncSession = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
):
    """Generate an appeal letter based on the original narrative and the denial reason."""
    from sqlalchemy.orm import selectinload

    # Get extraction
    result = await db.execute(
        select(ExtractionResult)
        .options(selectinload(ExtractionResult.ingestion_job))
        .where(ExtractionResult.id == extraction_id)
        .where(ExtractionResult.tenant_id == tenant.id)
    )
    ext = result.scalar_one_or_none()
    if not ext:
        raise HTTPException(status_code=404, detail="Extraction result not found")

    # Get the most recent narrative (what was originally submitted)
    narrative_result = await db.execute(
        select(PayerNarrative)
        .where(PayerNarrative.extraction_result_id == extraction_id)
        .order_by(PayerNarrative.created_at.desc())
        .limit(1)
    )
    original_narrative = narrative_result.scalar_one_or_none()

    extraction_data = OrthoPriorAuthData(
        diagnosis_code=ext.diagnosis_code or "Not found",
        procedure_cpt_codes=ext.procedure_cpt_codes or [],
        conservative_treatments_failed=ext.conservative_treatments_failed or [],
        implant_type_requested=ext.implant_type_requested or "Not specified",
        robotic_assistance_required=ext.robotic_assistance_required or False,
        clinical_justification=ext.clinical_justification or "",
        confidence_score=ext.confidence_score or 0.0,
    )

    # Build appeal context
    appeal_context_parts = [f"DENIAL REASON: {body.denial_reason}"]
    if original_narrative:
        appeal_context_parts.append(f"ORIGINAL SUBMISSION NARRATIVE:\n{original_narrative.narrative_text}")
    if body.additional_context:
        appeal_context_parts.append(f"ADDITIONAL SUPPORTING EVIDENCE:\n{body.additional_context}")

    # Look up payer criteria if we know the payer from the original narrative
    payer_name = original_narrative.payer if original_narrative else None
    procedure_name = original_narrative.procedure if original_narrative else None
    payer_criteria = None

    if payer_name and procedure_name:
        policy_result = await db.execute(
            select(PayerPolicy)
            .where(PayerPolicy.payer == payer_name)
            .where(PayerPolicy.procedure == procedure_name)
            .where(PayerPolicy.status == "active")
            .limit(1)
        )
        policy = policy_result.scalar_one_or_none()
        if policy:
            payer_criteria = policy.criteria

    from app.services.llm.narrative import generate_narrative as gen_narrative

    narrative_text, model_used, _, citations_raw = await gen_narrative(
        extraction_data,
        additional_context="\n\n".join(appeal_context_parts),
        payer_name=payer_name,
        procedure_name=procedure_name,
        payer_criteria=payer_criteria,
    )

    appeal_narrative = PayerNarrative(
        tenant_id=tenant.id,
        extraction_result_id=extraction_id,
        narrative_text=narrative_text,
        model_used=model_used,
        prompt_version="v4.0-appeal",
        payer=payer_name,
        procedure=procedure_name,
    )
    db.add(appeal_narrative)
    await db.commit()
    await db.refresh(appeal_narrative)

    # Save version 0
    v0 = NarrativeVersion(
        narrative_id=appeal_narrative.id,
        version_number=0,
        narrative_text=narrative_text,
        source="ai",
    )
    db.add(v0)

    # Update extraction outcome to appealed
    ext.outcome = "appealed"
    await db.commit()

    from app.core.audit import log_event
    await log_event(
        db, "appeal", "payer_narrative", appeal_narrative.id,
        metadata={
            "extraction_id": str(extraction_id),
            "denial_reason": body.denial_reason[:200],
            "original_narrative_id": str(original_narrative.id) if original_narrative else None,
        },
        tenant_id=tenant.id,
    )
    await db.commit()

    return NarrativeResponse(
        narrative_id=appeal_narrative.id,
        narrative_text=narrative_text,
        model_used=model_used,
        prompt_version="v4.0-appeal",
        payer=payer_name,
        procedure=procedure_name,
    )
