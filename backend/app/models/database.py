import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


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

    extraction_result: Mapped["ExtractionResult"] = relationship(back_populates="narratives")


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
