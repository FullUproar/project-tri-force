"""Add composite indexes on (tenant_id, created_at) for analytics query performance

Revision ID: 015
Revises: 014
Create Date: 2026-04-09
"""

from collections.abc import Sequence

from alembic import op

revision: str = "015"
down_revision: str | None = "014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_ingestion_jobs_tenant_created",
        "ingestion_jobs",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_extraction_results_tenant_created",
        "extraction_results",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_payer_narratives_tenant_created",
        "payer_narratives",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_audit_log_tenant_timestamp",
        "audit_log",
        ["tenant_id", "timestamp"],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_log_tenant_timestamp", table_name="audit_log")
    op.drop_index("ix_payer_narratives_tenant_created", table_name="payer_narratives")
    op.drop_index("ix_extraction_results_tenant_created", table_name="extraction_results")
    op.drop_index("ix_ingestion_jobs_tenant_created", table_name="ingestion_jobs")
