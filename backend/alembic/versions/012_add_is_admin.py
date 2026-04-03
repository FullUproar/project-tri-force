"""Add is_admin flag to organizations

Revision ID: 012
Revises: 011
Create Date: 2026-04-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "012"
down_revision: str | None = "011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("is_admin", sa.Boolean(), server_default="false"))
    # Default org is the CortaLoom team
    op.execute(
        "UPDATE organizations SET is_admin = true "
        "WHERE id = '00000000-0000-0000-0000-000000000001'"
    )


def downgrade() -> None:
    op.drop_column("organizations", "is_admin")
