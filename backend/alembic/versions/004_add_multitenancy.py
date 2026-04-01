"""Add multi-tenancy: organizations, api_keys, tenant_id on all tables

Revision ID: 004
Revises: 003
Create Date: 2026-04-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_ORG_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    # Create organizations table
    op.create_table(
        "organizations",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
    )

    # Create api_keys table
    op.create_table(
        "api_keys",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", sa.UUID(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
    )
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"])

    # Insert default organization for existing data
    op.execute(
        f"INSERT INTO organizations (id, name) VALUES ('{DEFAULT_ORG_ID}', 'Default Organization')"
    )

    # Add tenant_id to all data tables (nullable for backwards compat, then backfill)
    for table in ["ingestion_jobs", "extraction_results", "payer_narratives",
                  "clinical_note_embeddings", "audit_log"]:
        op.add_column(table, sa.Column("tenant_id", sa.UUID(), nullable=True))
        # Backfill existing rows
        op.execute(f"UPDATE {table} SET tenant_id = '{DEFAULT_ORG_ID}'")
        # Add FK and index
        op.create_foreign_key(
            f"fk_{table}_tenant_id", table, "organizations", ["tenant_id"], ["id"]
        )
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])


def downgrade() -> None:
    for table in ["audit_log", "clinical_note_embeddings", "payer_narratives",
                  "extraction_results", "ingestion_jobs"]:
        op.drop_index(f"ix_{table}_tenant_id")
        op.drop_constraint(f"fk_{table}_tenant_id", table, type_="foreignkey")
        op.drop_column(table, "tenant_id")

    op.drop_index("ix_api_keys_key_hash")
    op.drop_table("api_keys")
    op.drop_table("organizations")
