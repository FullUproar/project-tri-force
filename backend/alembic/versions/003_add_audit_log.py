"""Add audit_log table for HIPAA compliance

Revision ID: 003
Revises: 002
Create Date: 2026-04-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("resource_type", sa.String(30)),
        sa.Column("resource_id", sa.UUID()),
        sa.Column("request_id", sa.String(36)),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("metadata_json", sa.dialects.postgresql.JSONB()),
    )
    op.create_index("ix_audit_log_timestamp", "audit_log", ["timestamp"])
    op.create_index("ix_audit_log_action", "audit_log", ["action"])
    op.create_index("ix_audit_log_resource_id", "audit_log", ["resource_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_log_resource_id")
    op.drop_index("ix_audit_log_action")
    op.drop_index("ix_audit_log_timestamp")
    op.drop_table("audit_log")
