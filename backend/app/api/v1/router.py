from fastapi import APIRouter, Depends

from app.api.v1.admin import router as admin_router
from app.api.v1.extraction import router as extraction_router
from app.api.v1.ingest import router as ingest_router
from app.core.security import get_current_tenant

api_v1_router = APIRouter(dependencies=[Depends(get_current_tenant)])
api_v1_router.include_router(ingest_router, prefix="/ingest", tags=["ingestion"])
api_v1_router.include_router(extraction_router, tags=["extraction"])
api_v1_router.include_router(admin_router, tags=["admin"])
