"""Add policy document chunks, narrative citations, and knowledge graph tables

Revision ID: 014
Revises: 013
Create Date: 2026-04-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "014"
down_revision: str | None = "013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- Policy document storage ---
    op.create_table(
        "payer_policy_documents",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("payer", sa.String(50), nullable=False),
        sa.Column("procedure", sa.String(100)),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("source_url", sa.Text),
        sa.Column("source_hash", sa.String(64)),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("total_chunks", sa.Integer, server_default="0"),
        sa.Column("metadata_json", sa.dialects.postgresql.JSONB),
    )

    # --- Policy chunks (for RAG retrieval + citation) ---
    op.create_table(
        "payer_policy_chunks",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("payer_policy_documents.id")),
        sa.Column("policy_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("payer_policies.id")),
        sa.Column("payer", sa.String(50), nullable=False, index=True),
        sa.Column("procedure", sa.String(100), index=True),
        sa.Column("section_title", sa.String(300)),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("embedding", Vector(384)),
        sa.Column("page_number", sa.Integer),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("char_start", sa.Integer),
        sa.Column("char_end", sa.Integer),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_policy_chunks_payer_procedure", "payer_policy_chunks", ["payer", "procedure"])

    # --- Narrative citations ---
    op.create_table(
        "narrative_citations",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("narrative_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("payer_narratives.id"), index=True),
        sa.Column("marker", sa.String(10), nullable=False),
        sa.Column("claim_text", sa.Text, nullable=False),
        sa.Column("source_type", sa.String(20), nullable=False),
        sa.Column("source_chunk_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("payer_policy_chunks.id")),
        sa.Column("source_text", sa.Text),
        sa.Column("page_number", sa.Integer),
        sa.Column("section_title", sa.String(300)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- Knowledge graph ---
    op.create_table(
        "kg_nodes",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("node_type", sa.String(30), nullable=False),
        sa.Column("label", sa.String(300), nullable=False),
        sa.Column("properties", sa.dialects.postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_kg_nodes_type_label", "kg_nodes", ["node_type", "label"], unique=True)

    op.create_table(
        "kg_edges",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_node_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("kg_nodes.id"), index=True),
        sa.Column("target_node_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("kg_nodes.id"), index=True),
        sa.Column("edge_type", sa.String(30), nullable=False),
        sa.Column("properties", sa.dialects.postgresql.JSONB),
        sa.Column("confidence", sa.Float, server_default="1.0"),
        sa.Column("source_chunk_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("payer_policy_chunks.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_kg_edges_type", "kg_edges", ["edge_type"])


def downgrade() -> None:
    op.drop_table("kg_edges")
    op.drop_table("kg_nodes")
    op.drop_table("narrative_citations")
    op.drop_table("payer_policy_chunks")
    op.drop_table("payer_policy_documents")
