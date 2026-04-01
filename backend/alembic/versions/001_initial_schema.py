"""Initial schema with all Phase 1 tables

Revision ID: 001
Revises:
Create Date: 2026-03-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column("source_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("file_key", sa.String(500)),
        sa.Column("original_filename", sa.String(255)),
        sa.Column("file_size_bytes", sa.BigInteger()),
        sa.Column("metadata_json", sa.dialects.postgresql.JSONB()),
        sa.Column("error_message", sa.Text()),
    )

    op.create_table(
        "extraction_results",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "ingestion_job_id", sa.UUID(), sa.ForeignKey("ingestion_jobs.id"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column("diagnosis_code", sa.String(20)),
        sa.Column("conservative_treatments_failed", sa.dialects.postgresql.JSONB()),
        sa.Column("implant_type_requested", sa.String(100)),
        sa.Column("robotic_assistance_required", sa.Boolean()),
        sa.Column("clinical_justification", sa.Text()),
        sa.Column("confidence_score", sa.Float()),
        sa.Column("raw_extraction_json", sa.dialects.postgresql.JSONB()),
    )

    op.create_table(
        "payer_narratives",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "extraction_result_id",
            sa.UUID(),
            sa.ForeignKey("extraction_results.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column("narrative_text", sa.Text(), nullable=False),
        sa.Column("model_used", sa.String(50), nullable=False),
        sa.Column("prompt_version", sa.String(20), nullable=False),
    )

    op.create_table(
        "clinical_note_embeddings",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "ingestion_job_id", sa.UUID(), sa.ForeignKey("ingestion_jobs.id"), nullable=False
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536)),
    )


def downgrade() -> None:
    op.drop_table("clinical_note_embeddings")
    op.drop_table("payer_narratives")
    op.drop_table("extraction_results")
    op.drop_table("ingestion_jobs")
