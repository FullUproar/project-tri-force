import uuid as uuid_mod
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Request
from sqlalchemy import select, text
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


@app.on_event("startup")
async def purge_expired_data():
    """Delete completed jobs older than data_retention_days (HIPAA compliance)."""
    from datetime import timedelta

    from sqlalchemy import delete

    from app.config import settings
    from app.core.db import async_session
    from app.models.database import (
        ExtractionResult,
        IngestionJob,
        PayerNarrative,
    )

    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.data_retention_days)
    async with async_session() as session:
        # Delete narratives for old extractions
        old_extractions = (
            select(ExtractionResult.id)
            .join(IngestionJob)
            .where(IngestionJob.created_at < cutoff)
            .where(IngestionJob.status == "completed")
        )
        await session.execute(
            delete(PayerNarrative).where(
                PayerNarrative.extraction_result_id.in_(old_extractions)
            )
        )
        # Delete old extraction results
        await session.execute(
            delete(ExtractionResult).where(
                ExtractionResult.ingestion_job_id.in_(
                    select(IngestionJob.id)
                    .where(IngestionJob.created_at < cutoff)
                    .where(IngestionJob.status == "completed")
                )
            )
        )
        # Delete old jobs
        result = await session.execute(
            delete(IngestionJob)
            .where(IngestionJob.created_at < cutoff)
            .where(IngestionJob.status == "completed")
        )
        if result.rowcount > 0:
            await session.commit()
            logger.info("Purged %d expired jobs (>%d days)", result.rowcount, settings.data_retention_days)


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    import time

    from app.core.db import engine

    start = time.monotonic()
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
        db_latency_ms = round((time.monotonic() - start) * 1000, 1)
    except Exception:
        db_status = "unreachable"
        db_latency_ms = None

    pool = engine.pool
    try:
        pool_stats = {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
        }
    except AttributeError:
        pool_stats = {"type": type(pool).__name__}

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "database": db_status,
        "db_latency_ms": db_latency_ms,
        "pool": pool_stats,
        "service": "cortaloom-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "0.1.0",
    }
