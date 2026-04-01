from fastapi import FastAPI

from app.api.v1.router import api_v1_router
from app.core.logging import setup_logging
from app.core.security import add_cors_middleware

setup_logging()

app = FastAPI(
    title="Tri-Force API",
    description="Universal B2B AI Data Middleware for Clinical Data Normalization",
    version="0.1.0",
)

add_cors_middleware(app)
app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
