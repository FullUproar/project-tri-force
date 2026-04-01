import uuid as uuid_mod
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.router import api_v1_router
from app.core.logging import logger, request_id_var, setup_logging
from app.core.security import SecurityHeadersMiddleware, add_cors_middleware
from app.dependencies import get_db

setup_logging()

app = FastAPI(
    title="CortaLoom API",
    description="Universal B2B AI Data Middleware for Clinical Data Normalization",
    version="0.1.0",
)

add_cors_middleware(app)
app.add_middleware(SecurityHeadersMiddleware)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    rid = request.headers.get("X-Request-ID", str(uuid_mod.uuid4()))
    request_id_var.set(rid)
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response


app.include_router(api_v1_router, prefix="/api/v1")


@app.on_event("startup")
async def recover_stuck_jobs():
    """Mark jobs stuck in 'processing' for >10 minutes as failed."""
    from datetime import timedelta

    from sqlalchemy import update

    from app.core.db import async_session
    from app.models.database import IngestionJob

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
    async with async_session() as session:
        result = await session.execute(
            update(IngestionJob)
            .where(IngestionJob.status == "processing")
            .where(IngestionJob.created_at < cutoff)
            .values(status="failed", error_message="Server restart — please resubmit")
        )
        if result.rowcount > 0:
            await session.commit()
            logger.info("Recovered %d stuck jobs", result.rowcount)


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "unreachable"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "database": db_status,
        "service": "cortaloom-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "0.1.0",
    }
