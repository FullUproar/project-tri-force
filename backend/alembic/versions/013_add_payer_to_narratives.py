"""Add payer column to payer_narratives for payer-specific narrative tracking

Revision ID: 013
Revises: 012
Create Date: 2026-04-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "013"
down_revision: str | None = "012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "payer_narratives",
        sa.Column("payer", sa.String(50), nullable=True),
    )
    op.add_column(
        "payer_narratives",
        sa.Column("procedure", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("payer_narratives", "procedure")
    op.drop_column("payer_narratives", "payer")
