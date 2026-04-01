import hashlib
import uuid

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.config import settings
from app.dependencies import get_db
from app.models.database import ApiKey, Organization

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def hash_api_key(key: str) -> str:
    """SHA-256 hash of an API key for storage."""
    return hashlib.sha256(key.encode()).hexdigest()


async def get_current_tenant(
    request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: str = Security(api_key_header),
) -> Organization:
    """Validate API key and return the associated tenant Organization.

    Accepts key via X-API-Key header or api_key query param (for SSE).
    Falls back to legacy TF_API_KEY for backwards compatibility.
    """
    key = api_key or request.query_params.get("api_key")
    if not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )

    # Check DB-backed API keys first
    key_hash = hash_api_key(key)
    result = await db.execute(
        select(ApiKey)
        .options(selectinload(ApiKey.organization))
        .where(ApiKey.key_hash == key_hash)
        .where(ApiKey.is_active == True)  # noqa: E712
        .limit(1)
    )
    db_key = result.scalar_one_or_none()

    if db_key and db_key.organization and db_key.organization.is_active:
        if not db_key.organization.baa_signed_at:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Business Associate Agreement must be signed before uploading data. Contact support@cortaloom.ai.",
            )
        return db_key.organization

    # Fallback: legacy single API key (no tenant — returns default org)
    if key == settings.api_key.get_secret_value():
        # Load or create default org
        result = await db.execute(
            select(Organization).where(
                Organization.id == uuid.UUID("00000000-0000-0000-0000-000000000001")
            )
        )
        org = result.scalar_one_or_none()
        if org:
            return org

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
    )


def add_cors_middleware(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["X-API-Key", "Content-Type", "X-Request-ID"],
    )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response
