"""Add verticals to organizations and schema_version to extraction_results

Revision ID: 008
Revises: 007
Create Date: 2026-04-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: str | None = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("verticals", sa.dialects.postgresql.JSONB(), nullable=True))
    op.add_column("extraction_results", sa.Column("schema_version", sa.String(10), nullable=True))
    # Backfill existing orgs with ortho, existing extractions with ortho_v1
    op.execute("UPDATE organizations SET verticals = '[\"ortho\"]'::jsonb")
    op.execute("UPDATE extraction_results SET schema_version = 'ortho_v1'")


def downgrade() -> None:
    op.drop_column("extraction_results", "schema_version")
    op.drop_column("organizations", "verticals")
