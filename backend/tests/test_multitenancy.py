"""Multi-tenancy isolation tests.

Verifies that tenants cannot see each other's data.
"""

import hashlib

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.db import async_session
from app.core.security import hash_api_key
from app.main import app
from app.models.database import ApiKey, IngestionJob, Organization


async def _create_tenant(name: str, api_key_raw: str) -> tuple[str, str]:
    """Create an org + API key in the DB, or return existing. Returns (org_id, raw_key)."""
    from sqlalchemy import select

    async with async_session() as db:
        # Check if key already exists
        existing = await db.execute(
            select(ApiKey).where(ApiKey.key_hash == hash_api_key(api_key_raw)).limit(1)
        )
        if existing.scalar_one_or_none():
            return "", api_key_raw

        org = Organization(name=name)
        db.add(org)
        await db.flush()

        key = ApiKey(
            organization_id=org.id,
            key_hash=hash_api_key(api_key_raw),
            name=f"{name} key",
        )
        db.add(key)
        await db.commit()
        return str(org.id), api_key_raw


@pytest.mark.asyncio
async def test_tenant_isolation_jobs():
    """Tenant A cannot see Tenant B's jobs."""
    _, key_a = await _create_tenant("ASC Alpha", "test-key-alpha-12345")
    _, key_b = await _create_tenant("ASC Beta", "test-key-beta-67890")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Tenant A uploads a clinical note
        resp_a = await client.post(
            "/api/v1/ingest/clinical-note",
            headers={"X-API-Key": "test-key-alpha-12345"},
            files={"file": ("note_a.txt", b"Tenant A patient has knee OA. Failed NSAIDs and PT.", "text/plain")},
        )
        assert resp_a.status_code == 200
        job_a_id = resp_a.json()["job_id"]

        # Tenant B uploads a clinical note
        resp_b = await client.post(
            "/api/v1/ingest/clinical-note",
            headers={"X-API-Key": "test-key-beta-67890"},
            files={"file": ("note_b.txt", b"Tenant B patient needs hip replacement. Failed conservative care.", "text/plain")},
        )
        assert resp_b.status_code == 200
        job_b_id = resp_b.json()["job_id"]

        # Tenant A lists jobs — should only see their own
        list_a = await client.get("/api/v1/ingest/jobs", headers={"X-API-Key": "test-key-alpha-12345"})
        assert list_a.status_code == 200
        a_job_ids = [j["job_id"] for j in list_a.json()]
        assert job_a_id in a_job_ids
        assert job_b_id not in a_job_ids

        # Tenant B lists jobs — should only see their own
        list_b = await client.get("/api/v1/ingest/jobs", headers={"X-API-Key": "test-key-beta-67890"})
        assert list_b.status_code == 200
        b_job_ids = [j["job_id"] for j in list_b.json()]
        assert job_b_id in b_job_ids
        assert job_a_id not in b_job_ids


@pytest.mark.asyncio
async def test_invalid_api_key_rejected():
    """Non-existent API key returns 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/ingest/jobs",
            headers={"X-API-Key": "completely-fake-key-that-doesnt-exist"},
        )
        assert resp.status_code == 401
