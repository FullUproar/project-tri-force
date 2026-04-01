"""Add Stripe billing columns to organizations

Revision ID: 007
Revises: 006
Create Date: 2026-04-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("stripe_customer_id", sa.String(100), nullable=True))
    op.add_column("organizations", sa.Column("subscription_status", sa.String(20), nullable=True))
    op.create_index("ix_organizations_stripe_customer_id", "organizations", ["stripe_customer_id"])
    # Default org gets trialing status
    op.execute(
        "UPDATE organizations SET subscription_status = 'trialing' "
        "WHERE id = '00000000-0000-0000-0000-000000000001'"
    )


def downgrade() -> None:
    op.drop_index("ix_organizations_stripe_customer_id")
    op.drop_column("organizations", "subscription_status")
    op.drop_column("organizations", "stripe_customer_id")
