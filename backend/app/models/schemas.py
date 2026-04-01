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


class NarrativeResponse(BaseModel):
    narrative_id: uuid.UUID
    narrative_text: str
    model_used: str
    prompt_version: str


# --- SSE Schemas ---


class ProcessingStatusEvent(BaseModel):
    status: str
    step: str
    progress: float
