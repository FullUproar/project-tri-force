"""Add tiered billing fields to organizations

Revision ID: 009
Revises: 008
Create Date: 2026-04-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "009"
down_revision: str | None = "008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("subscription_tier", sa.String(20), nullable=True))
    op.add_column("organizations", sa.Column("monthly_extraction_count", sa.Integer(), server_default="0"))
    op.add_column("organizations", sa.Column("billing_cycle_start", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("organizations", "billing_cycle_start")
    op.drop_column("organizations", "monthly_extraction_count")
    op.drop_column("organizations", "subscription_tier")
