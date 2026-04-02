"""Add budget cap and alert tracking to organizations

Revision ID: 010
Revises: 009
Create Date: 2026-04-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "010"
down_revision: str | None = "009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("overage_budget_cap", sa.Float(), nullable=True))
    op.add_column("organizations", sa.Column("alert_at_80_sent", sa.Boolean(), server_default="false"))
    op.add_column("organizations", sa.Column("alert_at_100_sent", sa.Boolean(), server_default="false"))


def downgrade() -> None:
    op.drop_column("organizations", "alert_at_100_sent")
    op.drop_column("organizations", "alert_at_80_sent")
    op.drop_column("organizations", "overage_budget_cap")
