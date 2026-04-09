from __future__ import annotations

import uuid
from datetime import datetime
from typing import NewType

from pydantic import BaseModel, Field

# Type-safe wrapper: only PHI-scrubbed text can be passed to LLM services
ScrubbedText = NewType("ScrubbedText", str)


# --- Ingestion Schemas ---


class IngestionResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    message: str | None = None
    metadata: dict | None = None
    file_key: str | None = None


class JobStatusResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    source_type: str
    created_at: datetime
    extraction_result: ExtractionResultResponse | None = None
    error_message: str | None = None


# --- Extraction Schemas ---


class OrthoPriorAuthData(BaseModel):
    """Structured extraction target for orthopaedic prior authorization."""

    diagnosis_code: str = Field(description="ICD-10 code, e.g. M17.11")
    conservative_treatments_failed: list[str] = Field(
        default_factory=list,
        description="List of conservative treatments attempted and failed",
    )
    implant_type_requested: str = Field(
        default="Not specified", description="Specific implant system name"
    )
    robotic_assistance_required: bool = Field(default=False)
    clinical_justification: str = Field(
        default="", description="2-3 sentence clinical summary justifying the procedure"
    )
    confidence_score: float = Field(
        default=0.0, description="Confidence in extraction accuracy, 0.0 to 1.0"
    )


class SpinePainPriorAuthData(BaseModel):
    """Structured extraction for spine surgery and pain management prior authorization."""

    diagnosis_code: str = Field(description="ICD-10 code, e.g. M54.5, G89.4, M47.816")
    procedure_cpt_code: str = Field(
        default="", description="CPT code, e.g. 63650 (SCS trial), 62322 (epidural)"
    )
    conservative_treatments_failed: list[str] = Field(
        default_factory=list,
        description="Conservative treatments with durations (e.g., 'PT x 6 weeks', 'NSAIDs x 3 months')",
    )
    imaging_findings: str = Field(
        default="", description="MRI/CT findings (disc herniation, stenosis, etc.)"
    )
    imaging_date: str = Field(
        default="", description="Date of most recent imaging (YYYY-MM-DD)"
    )
    symptom_duration_months: int = Field(
        default=0, description="Duration of symptoms in months"
    )
    functional_impairment: str = Field(
        default="", description="Description of functional limitation"
    )
    prior_surgical_history: str = Field(
        default="", description="Previous spine/pain surgeries (e.g., prior laminectomy)"
    )
    device_requested: str = Field(
        default="Not specified", description="Spinal cord stimulator, intrathecal pump, implant system"
    )
    clinical_justification: str = Field(
        default="", description="2-3 sentence clinical summary"
    )
    confidence_score: float = Field(
        default=0.0, description="Confidence in extraction accuracy, 0.0 to 1.0"
    )


class ExtractionResultResponse(BaseModel):
    id: uuid.UUID
    diagnosis_code: str | None
    conservative_treatments_failed: list[str] | None
    implant_type_requested: str | None
    robotic_assistance_required: bool | None
    clinical_justification: str | None
    confidence_score: float | None
    outcome: str | None


class ClinicalNoteRequest(BaseModel):
    text: str


# --- Narrative Schemas ---


class GenerateNarrativeRequest(BaseModel):
    payer: str | None = None  # e.g., "UHC", "Aetna", "BCBS", "Cigna", "Humana"
    procedure: str | None = None  # e.g., "Total Knee Replacement"


class CitationResponse(BaseModel):
    marker: str
    claim: str
    source_type: str  # clinical_note, payer_policy
    source_text: str | None = None
    section_title: str | None = None


class NarrativeResponse(BaseModel):
    narrative_id: uuid.UUID
    narrative_text: str
    model_used: str
    prompt_version: str
    payer: str | None = None
    procedure: str | None = None
    citations: list[CitationResponse] | None = None


# --- SSE Schemas ---


class ProcessingStatusEvent(BaseModel):
    status: str
    step: str
    progress: float
