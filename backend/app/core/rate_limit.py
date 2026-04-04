"""Rate limiting using slowapi, keyed on client IP (supports X-Forwarded-For)."""

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def _get_client_ip(request: Request) -> str:
    """Extract client IP, preferring X-Forwarded-For for reverse proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # First IP in the chain is the real client
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=_get_client_ip, default_limits=["120/minute"])

# Limit strings for reuse across endpoints
RATE_AUTH_INGESTION = "30/minute"
RATE_GENERAL_API = "120/minute"
