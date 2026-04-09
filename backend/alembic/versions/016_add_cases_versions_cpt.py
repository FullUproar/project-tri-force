"""Add cases table, narrative_versions, case_id on ingestion_jobs, procedure_cpt_codes on extraction_results

Revision ID: 016
Revises: 015
Create Date: 2026-04-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "016"
down_revision: str | None = "015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- Cases table ---
    op.create_table(
        "cases",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False, index=True),
        sa.Column("short_id", sa.String(10), nullable=False, index=True),
        sa.Column("label", sa.String(200)),
        sa.Column("status", sa.String(20), server_default="open"),
        sa.Column("denial_reason", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "short_id", name="uq_case_tenant_short_id"),
    )

    # --- case_id FK on ingestion_jobs ---
    op.add_column(
        "ingestion_jobs",
        sa.Column("case_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("cases.id")),
    )
    op.create_index("ix_ingestion_jobs_case_id", "ingestion_jobs", ["case_id"])

    # --- procedure_cpt_codes on extraction_results ---
    op.add_column(
        "extraction_results",
        sa.Column("procedure_cpt_codes", sa.dialects.postgresql.JSONB),
    )

    # --- Narrative versions table ---
    op.create_table(
        "narrative_versions",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("narrative_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("payer_narratives.id"), nullable=False, index=True),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("narrative_text", sa.Text, nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("narrative_versions")
    op.drop_column("extraction_results", "procedure_cpt_codes")
    op.drop_index("ix_ingestion_jobs_case_id", table_name="ingestion_jobs")
    op.drop_column("ingestion_jobs", "case_id")
    op.drop_table("cases")
