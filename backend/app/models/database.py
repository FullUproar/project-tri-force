import random
import string
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


# Characters for short case IDs — no ambiguous chars (0/O, 1/I/L)
_SHORT_ID_CHARS = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def generate_short_id(length: int = 4) -> str:
    """Generate a human-readable short ID like 'CL-7K3M'."""
    return "CL-" + "".join(random.choices(_SHORT_ID_CHARS, k=length))


class Base(DeclarativeBase):
    pass


# --- Cases ---


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    short_id: Mapped[str] = mapped_column(String(10), index=True)
    label: Mapped[str | None] = mapped_column(String(200))  # optional user-provided label
    status: Mapped[str] = mapped_column(String(20), default="open")  # open, submitted, approved, denied, appealed
    denial_reason: Mapped[str | None] = mapped_column(Text)  # user-entered denial reason for appeals
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "short_id", name="uq_case_tenant_short_id"),
    )

    jobs: Mapped[list["IngestionJob"]] = relationship(back_populates="case")


# --- Multi-tenancy ---


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    baa_signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stripe_customer_id: Mapped[str | None] = mapped_column(String(100))
    subscription_status: Mapped[str | None] = mapped_column(String(20))  # active, past_due, canceled, trialing
    verticals: Mapped[list | None] = mapped_column(JSONB)  # ["ortho"], ["ortho", "spine"], etc.
    subscription_tier: Mapped[str | None] = mapped_column(String(20))  # starter, professional, enterprise
    monthly_extraction_count: Mapped[int] = mapped_column(Integer, default=0)
    billing_cycle_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    overage_budget_cap: Mapped[float | None] = mapped_column(Float)  # Max overage spend in $ (null = unlimited)
    alert_at_80_sent: Mapped[bool] = mapped_column(Boolean, default=False)  # Reset each billing cycle
    alert_at_100_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)  # True for CortaLoom team, False for ASC customers

    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="organization")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id")
    )
    key_hash: Mapped[str] = mapped_column(String(64))  # SHA-256 of the API key
    name: Mapped[str] = mapped_column(String(100))  # e.g., "Production", "Staging"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    organization: Mapped["Organization"] = relationship(back_populates="api_keys")


# --- Core Data Models ---


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    source_type: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    file_key: Mapped[str | None] = mapped_column(String(500))
    original_filename: Mapped[str | None] = mapped_column(String(255))
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)

    case: Mapped["Case | None"] = relationship(back_populates="jobs")
    extraction_result: Mapped["ExtractionResult | None"] = relationship(
        back_populates="ingestion_job"
    )


class ExtractionResult(Base):
    __tablename__ = "extraction_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    ingestion_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingestion_jobs.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    diagnosis_code: Mapped[str | None] = mapped_column(String(20))
    conservative_treatments_failed: Mapped[list | None] = mapped_column(JSONB)
    implant_type_requested: Mapped[str | None] = mapped_column(String(100))
    robotic_assistance_required: Mapped[bool | None] = mapped_column(Boolean)
    clinical_justification: Mapped[str | None] = mapped_column(Text)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    raw_extraction_json: Mapped[dict | None] = mapped_column(JSONB)
    outcome: Mapped[str | None] = mapped_column(String(20))  # approved, denied, pending, appealed
    schema_version: Mapped[str | None] = mapped_column(String(10), default="ortho_v1")  # ortho_v1, spine_v1, dental_v1
    procedure_cpt_codes: Mapped[list | None] = mapped_column(JSONB)  # e.g. ["27447", "S2900"]

    ingestion_job: Mapped["IngestionJob"] = relationship(back_populates="extraction_result")
    narratives: Mapped[list["PayerNarrative"]] = relationship(back_populates="extraction_result")


class PayerNarrative(Base):
    __tablename__ = "payer_narratives"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    extraction_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("extraction_results.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    narrative_text: Mapped[str] = mapped_column(Text)
    model_used: Mapped[str] = mapped_column(String(50))
    prompt_version: Mapped[str] = mapped_column(String(20))
    payer: Mapped[str | None] = mapped_column(String(50))
    procedure: Mapped[str | None] = mapped_column(String(100))

    extraction_result: Mapped["ExtractionResult"] = relationship(back_populates="narratives")
    versions: Mapped[list["NarrativeVersion"]] = relationship(back_populates="narrative", order_by="NarrativeVersion.version_number")


class NarrativeVersion(Base):
    """Full snapshot of narrative text at each version for liability trail and undo."""
    __tablename__ = "narrative_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    narrative_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payer_narratives.id"), index=True
    )
    version_number: Mapped[int] = mapped_column(Integer)
    narrative_text: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(20))  # "ai" or "human_edit"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    narrative: Mapped["PayerNarrative"] = relationship(back_populates="versions")


class ClinicalNoteEmbedding(Base):
    __tablename__ = "clinical_note_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    ingestion_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingestion_jobs.id")
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    embedding = mapped_column(Vector(1536))


class PayerPolicy(Base):
    __tablename__ = "payer_policies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    payer: Mapped[str] = mapped_column(String(50))  # UHC, Aetna, BCBS, Cigna, Humana
    procedure: Mapped[str] = mapped_column(String(100))  # Knee Replacement, Lumbar Fusion
    criteria: Mapped[dict] = mapped_column(JSONB)  # Structured requirements
    source_url: Mapped[str | None] = mapped_column(Text)
    source_hash: Mapped[str | None] = mapped_column(String(64))  # SHA-256 for change detection
    version: Mapped[int] = mapped_column(Integer, default=1)
    effective_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    changelog: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, pending_review, deprecated
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PayerPolicyDocument(Base):
    __tablename__ = "payer_policy_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    payer: Mapped[str] = mapped_column(String(50))
    procedure: Mapped[str | None] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(300))
    source_url: Mapped[str | None] = mapped_column(Text)
    source_hash: Mapped[str | None] = mapped_column(String(64))
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    status: Mapped[str] = mapped_column(String(20), default="active")
    total_chunks: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB)

    chunks: Mapped[list["PayerPolicyChunk"]] = relationship(back_populates="document")


class PayerPolicyChunk(Base):
    __tablename__ = "payer_policy_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payer_policy_documents.id")
    )
    policy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payer_policies.id")
    )
    payer: Mapped[str] = mapped_column(String(50), index=True)
    procedure: Mapped[str | None] = mapped_column(String(100), index=True)
    section_title: Mapped[str | None] = mapped_column(String(300))
    content: Mapped[str] = mapped_column(Text)
    embedding = mapped_column(Vector(384))
    page_number: Mapped[int | None] = mapped_column(Integer)
    chunk_index: Mapped[int] = mapped_column(Integer)
    char_start: Mapped[int | None] = mapped_column(Integer)
    char_end: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    document: Mapped["PayerPolicyDocument | None"] = relationship(back_populates="chunks")


class NarrativeCitation(Base):
    __tablename__ = "narrative_citations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    narrative_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payer_narratives.id"), index=True
    )
    marker: Mapped[str] = mapped_column(String(10))
    claim_text: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(20))  # clinical_note, payer_policy
    source_chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payer_policy_chunks.id")
    )
    source_text: Mapped[str | None] = mapped_column(Text)
    page_number: Mapped[int | None] = mapped_column(Integer)
    section_title: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    source_chunk: Mapped["PayerPolicyChunk | None"] = relationship()


class KGNode(Base):
    __tablename__ = "kg_nodes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    node_type: Mapped[str] = mapped_column(String(30))  # payer, procedure, criterion, diagnosis, treatment, requirement
    label: Mapped[str] = mapped_column(String(300))
    properties: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    outgoing_edges: Mapped[list["KGEdge"]] = relationship(
        foreign_keys="KGEdge.source_node_id", back_populates="source_node"
    )
    incoming_edges: Mapped[list["KGEdge"]] = relationship(
        foreign_keys="KGEdge.target_node_id", back_populates="target_node"
    )


class KGEdge(Base):
    __tablename__ = "kg_edges"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("kg_nodes.id"), index=True
    )
    target_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("kg_nodes.id"), index=True
    )
    edge_type: Mapped[str] = mapped_column(String(30))  # requires, strengthens, treats, diagnosed_with, has_criterion
    properties: Mapped[dict | None] = mapped_column(JSONB)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    source_chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payer_policy_chunks.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    source_node: Mapped["KGNode"] = relationship(foreign_keys=[source_node_id], back_populates="outgoing_edges")
    target_node: Mapped["KGNode"] = relationship(foreign_keys=[target_node_id], back_populates="incoming_edges")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    action: Mapped[str] = mapped_column(String(50))
    resource_type: Mapped[str | None] = mapped_column(String(30))
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    request_id: Mapped[str | None] = mapped_column(String(36))
    ip_address: Mapped[str | None] = mapped_column(String(45))
    metadata_json: Mapped[dict | None] = mapped_column(JSONB)
