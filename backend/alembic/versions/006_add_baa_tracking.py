"""Add baa_signed_at to organizations for HIPAA BAA tracking

Revision ID: 006
Revises: 005
Create Date: 2026-04-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("baa_signed_at", sa.DateTime(timezone=True), nullable=True))
    # Backfill default org as BAA-signed (it's your own org)
    op.execute(
        "UPDATE organizations SET baa_signed_at = now() "
        "WHERE id = '00000000-0000-0000-0000-000000000001'"
    )


def downgrade() -> None:
    op.drop_column("organizations", "baa_signed_at")
