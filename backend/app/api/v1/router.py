from fastapi import APIRouter, Depends

from app.api.v1.extraction import router as extraction_router
from app.api.v1.ingest import router as ingest_router
from app.core.security import verify_api_key

api_v1_router = APIRouter(dependencies=[Depends(verify_api_key)])
api_v1_router.include_router(ingest_router, prefix="/ingest", tags=["ingestion"])
api_v1_router.include_router(extraction_router, tags=["extraction"])
