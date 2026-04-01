"""Add indexes for frequently queried columns

Revision ID: 002
Revises: 001
Create Date: 2026-04-01
"""

from collections.abc import Sequence

from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_ingestion_jobs_status", "ingestion_jobs", ["status"])
    op.create_index("ix_ingestion_jobs_created_at", "ingestion_jobs", ["created_at"])
    op.create_index(
        "ix_extraction_results_ingestion_job_id",
        "extraction_results",
        ["ingestion_job_id"],
    )
    op.create_index(
        "ix_payer_narratives_extraction_result_id",
        "payer_narratives",
        ["extraction_result_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_payer_narratives_extraction_result_id")
    op.drop_index("ix_extraction_results_ingestion_job_id")
    op.drop_index("ix_ingestion_jobs_created_at")
    op.drop_index("ix_ingestion_jobs_status")
