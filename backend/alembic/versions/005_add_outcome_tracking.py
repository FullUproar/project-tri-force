"""Add outcome column to extraction_results for prior auth tracking

Revision ID: 005
Revises: 004
Create Date: 2026-04-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("extraction_results", sa.Column("outcome", sa.String(20), nullable=True))
    op.create_index("ix_extraction_results_outcome", "extraction_results", ["outcome"])


def downgrade() -> None:
    op.drop_index("ix_extraction_results_outcome")
    op.drop_column("extraction_results", "outcome")
