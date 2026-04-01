"""HIPAA audit logging — records all data access and LLM operations.

Never logs clinical content. Only logs actions, resource IDs, and metadata
like token counts and latency.
"""

import uuid
from datetime import datetime, timezone

from app.core.logging import logger, request_id_var
from app.models.database import AuditLog


async def log_event(
    db_session,
    action: str,
    resource_type: str | None = None,
    resource_id: uuid.UUID | None = None,
    ip_address: str | None = None,
    metadata: dict | None = None,
):
    """Write an audit log entry. Fire-and-forget — errors are logged, not raised."""
    try:
        entry = AuditLog(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            request_id=request_id_var.get(""),
            ip_address=ip_address,
            metadata_json=metadata,
        )
        db_session.add(entry)
        await db_session.flush()
    except Exception as e:
        logger.error("Failed to write audit log: %s", str(e))


async def log_event_standalone(
    action: str,
    resource_type: str | None = None,
    resource_id: uuid.UUID | None = None,
    ip_address: str | None = None,
    metadata: dict | None = None,
):
    """Write an audit log using a standalone session (for background tasks)."""
    from app.core.db import async_session

    try:
        async with async_session() as db:
            entry = AuditLog(
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                request_id=request_id_var.get(""),
                ip_address=ip_address,
                metadata_json=metadata,
            )
            db.add(entry)
            await db.commit()
    except Exception as e:
        logger.error("Failed to write audit log: %s", str(e))
