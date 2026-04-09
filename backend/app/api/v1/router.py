from fastapi import APIRouter, Depends

from app.api.v1.admin import router as admin_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.billing import router as billing_router
from app.api.v1.extraction import router as extraction_router
from app.api.v1.graph import router as graph_router
from app.api.v1.ingest import router as ingest_router
from app.api.v1.payer_policy import router as payer_policy_router
from app.api.v1.policy_docs import router as policy_docs_router
from app.core.security import get_current_tenant

api_v1_router = APIRouter(dependencies=[Depends(get_current_tenant)])
api_v1_router.include_router(ingest_router, prefix="/ingest", tags=["ingestion"])
api_v1_router.include_router(extraction_router, tags=["extraction"])
api_v1_router.include_router(admin_router, tags=["admin"])
api_v1_router.include_router(analytics_router, tags=["analytics"])
api_v1_router.include_router(billing_router, tags=["billing"])
api_v1_router.include_router(payer_policy_router, tags=["payer-policy"])
api_v1_router.include_router(policy_docs_router, tags=["policy-docs"])
api_v1_router.include_router(graph_router, tags=["knowledge-graph"])
