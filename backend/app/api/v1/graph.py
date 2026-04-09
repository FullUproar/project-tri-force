"""Knowledge graph query endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_admin_tenant, get_current_tenant
from app.dependencies import get_db
from app.models.database import KGEdge, KGNode, Organization
from app.services.knowledge_graph import (
    build_graph_from_policies,
    find_cross_payer_insights,
    get_related_requirements,
)

router = APIRouter()


@router.post("/graph/build")
async def build_graph(
    db: AsyncSession = Depends(get_db),
    _tenant: Organization = Depends(get_admin_tenant),
):
    """Build the knowledge graph from payer policies. Admin-only."""
    result = await build_graph_from_policies(db)
    return {"nodes_created": result["nodes_created"], "edges_created": result["edges_created"]}


@router.get("/graph/requirements")
async def graph_requirements(
    payer: str = Query(..., description="Payer name"),
    procedure: str = Query(..., description="Procedure name"),
    db: AsyncSession = Depends(get_db),
    _tenant: Organization = Depends(get_current_tenant),
):
    """Query the graph for requirements for a given payer and procedure."""
    requirements = await get_related_requirements(db, payer, procedure)
    return requirements


@router.get("/graph/insights")
async def graph_insights(
    procedure: str = Query(..., description="Procedure name"),
    diagnosis_code: str | None = Query(None, description="Optional ICD-10 diagnosis code"),
    db: AsyncSession = Depends(get_db),
    _tenant: Organization = Depends(get_current_tenant),
):
    """Get cross-payer insights for a procedure, optionally filtered by diagnosis code."""
    insights = await find_cross_payer_insights(db, procedure, diagnosis_code)
    return insights


@router.get("/graph/stats")
async def graph_stats(
    db: AsyncSession = Depends(get_db),
    _tenant: Organization = Depends(get_current_tenant),
):
    """Return node count by type and edge count by type."""
    node_result = await db.execute(
        select(KGNode.node_type, func.count().label("count"))
        .group_by(KGNode.node_type)
        .order_by(KGNode.node_type)
    )
    nodes_by_type = {row.node_type: row.count for row in node_result.all()}

    edge_result = await db.execute(
        select(KGEdge.edge_type, func.count().label("count"))
        .group_by(KGEdge.edge_type)
        .order_by(KGEdge.edge_type)
    )
    edges_by_type = {row.edge_type: row.count for row in edge_result.all()}

    return {
        "nodes_by_type": nodes_by_type,
        "edges_by_type": edges_by_type,
        "total_nodes": sum(nodes_by_type.values()),
        "total_edges": sum(edges_by_type.values()),
    }
