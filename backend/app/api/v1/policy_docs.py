"""Policy document management and chunk seeding endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_admin_tenant, get_current_tenant
from app.dependencies import get_db
from app.models.database import NarrativeCitation, Organization, PayerPolicyChunk

router = APIRouter()


@router.post("/policy-docs/seed-chunks")
async def seed_chunks(
    db: AsyncSession = Depends(get_db),
    _tenant: Organization = Depends(get_admin_tenant),
):
    """Generate chunks from existing payer policies. Admin-only."""
    from app.services.policy_ingestion import seed_chunks_from_policies

    chunks_created = await seed_chunks_from_policies(db)
    return {"chunks_created": chunks_created}


@router.get("/policy-docs/chunks")
async def list_chunks(
    payer: str | None = Query(None, description="Filter by payer name"),
    procedure: str | None = Query(None, description="Filter by procedure"),
    db: AsyncSession = Depends(get_db),
    _tenant: Organization = Depends(get_current_tenant),
):
    """List policy chunks with optional filters."""
    query = select(PayerPolicyChunk)
    if payer:
        query = query.where(PayerPolicyChunk.payer == payer)
    if procedure:
        query = query.where(PayerPolicyChunk.procedure == procedure)
    query = query.order_by(PayerPolicyChunk.payer, PayerPolicyChunk.chunk_index)

    result = await db.execute(query)
    chunks = result.scalars().all()

    return [
        {
            "id": str(c.id),
            "payer": c.payer,
            "procedure": c.procedure,
            "section_title": c.section_title,
            "content": c.content,
            "chunk_index": c.chunk_index,
        }
        for c in chunks
    ]


@router.get("/policy-docs/chunks/{chunk_id}")
async def get_chunk(
    chunk_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _tenant: Organization = Depends(get_current_tenant),
):
    """Get a single policy chunk by ID."""
    chunk = await db.get(PayerPolicyChunk, chunk_id)
    if not chunk:
        raise HTTPException(status_code=404, detail="Chunk not found")

    return {
        "id": str(chunk.id),
        "payer": chunk.payer,
        "procedure": chunk.procedure,
        "section_title": chunk.section_title,
        "content": chunk.content,
        "chunk_index": chunk.chunk_index,
        "document_id": str(chunk.document_id) if chunk.document_id else None,
        "policy_id": str(chunk.policy_id) if chunk.policy_id else None,
        "page_number": chunk.page_number,
        "char_start": chunk.char_start,
        "char_end": chunk.char_end,
        "created_at": chunk.created_at.isoformat(),
    }


@router.get("/citations/{narrative_id}")
async def get_citations(
    narrative_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _tenant: Organization = Depends(get_current_tenant),
):
    """Get all citations for a narrative."""
    result = await db.execute(
        select(NarrativeCitation)
        .where(NarrativeCitation.narrative_id == narrative_id)
        .order_by(NarrativeCitation.marker)
    )
    citations = result.scalars().all()

    return [
        {
            "id": str(c.id),
            "marker": c.marker,
            "claim_text": c.claim_text,
            "source_type": c.source_type,
            "source_text": c.source_text,
            "section_title": c.section_title,
            "source_chunk_id": str(c.source_chunk_id) if c.source_chunk_id else None,
        }
        for c in citations
    ]
