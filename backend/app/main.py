from datetime import datetime, timezone

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.router import api_v1_router
from app.core.logging import setup_logging
from app.core.security import add_cors_middleware
from app.dependencies import get_db

setup_logging()

app = FastAPI(
    title="CortaLoom API",
    description="Universal B2B AI Data Middleware for Clinical Data Normalization",
    version="0.1.0",
)

add_cors_middleware(app)
app.include_router(api_v1_router, prefix="/api/v1")


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
