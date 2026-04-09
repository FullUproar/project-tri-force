"""Multi-tenancy isolation tests.

Verifies that tenants cannot see each other's data across ALL endpoints.
Data is inserted directly into the DB to avoid external dependencies (S3/MinIO).
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.db import async_session
from app.core.security import hash_api_key
from app.main import app
from app.models.database import ApiKey, ExtractionResult, IngestionJob, Organization


async def _create_tenant(name: str, api_key_raw: str) -> tuple[uuid.UUID, str]:
    """Create an org + API key in the DB, or return existing. Returns (org_id, raw_key)."""
    from datetime import datetime, timezone

    async with async_session() as db:
        # Check if key already exists
        existing = await db.execute(
            select(ApiKey)
            .options(selectinload(ApiKey.organization))
            .where(ApiKey.key_hash == hash_api_key(api_key_raw))
            .limit(1)
        )
        existing_key = existing.scalar_one_or_none()
        if existing_key:
            if existing_key.organization and not existing_key.organization.baa_signed_at:
                existing_key.organization.baa_signed_at = datetime.now(timezone.utc)
                await db.commit()
            return existing_key.organization_id, api_key_raw

        org = Organization(name=name, baa_signed_at=datetime.now(timezone.utc))
        db.add(org)
        await db.flush()

        key = ApiKey(
            organization_id=org.id,
            key_hash=hash_api_key(api_key_raw),
            name=f"{name} key",
        )
        db.add(key)
        await db.commit()
        return org.id, api_key_raw


async def _create_job(tenant_id: uuid.UUID, status: str = "completed") -> uuid.UUID:
    """Insert a job directly into the DB for a given tenant."""
    async with async_session() as db:
        job = IngestionJob(
            tenant_id=tenant_id,
            source_type="clinical_note",
            status=status,
            original_filename="test-note.txt",
            file_size_bytes=100,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        return job.id


async def _create_extraction(tenant_id: uuid.UUID, job_id: uuid.UUID) -> uuid.UUID:
    """Insert an extraction result directly into the DB for a given tenant."""
    async with async_session() as db:
        ext = ExtractionResult(
            tenant_id=tenant_id,
            ingestion_job_id=job_id,
            diagnosis_code="M17.11",
            conservative_treatments_failed=["NSAIDs", "PT"],
            implant_type_requested="Total knee",
            robotic_assistance_required=False,
            clinical_justification="End-stage OA with bone-on-bone changes",
            confidence_score=0.92,
            outcome="pending",
        )
        db.add(ext)
        await db.commit()
        await db.refresh(ext)
        return ext.id


# ---------------------------------------------------------------------------
# Job list isolation (pre-existing test, rewritten to use DB inserts)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tenant_isolation_jobs():
    """Tenant A cannot see Tenant B's jobs in the job list."""
    tenant_a_id, key_a = await _create_tenant("ASC Alpha", "test-key-alpha-12345")
    tenant_b_id, key_b = await _create_tenant("ASC Beta", "test-key-beta-67890")

    job_a_id = await _create_job(tenant_a_id)
    job_b_id = await _create_job(tenant_b_id)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Tenant A lists jobs — should only see their own
        list_a = await client.get("/api/v1/ingest/jobs", headers={"X-API-Key": key_a})
        assert list_a.status_code == 200
        a_job_ids = [j["job_id"] for j in list_a.json()]
        assert str(job_a_id) in a_job_ids
        assert str(job_b_id) not in a_job_ids

        # Tenant B lists jobs — should only see their own
        list_b = await client.get("/api/v1/ingest/jobs", headers={"X-API-Key": key_b})
        assert list_b.status_code == 200
        b_job_ids = [j["job_id"] for j in list_b.json()]
        assert str(job_b_id) in b_job_ids
        assert str(job_a_id) not in b_job_ids


# ---------------------------------------------------------------------------
# GET /jobs/{job_id} — cross-tenant read blocked
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cross_tenant_get_job_blocked():
    """Tenant B cannot read Tenant A's job by ID (IDOR prevention)."""
    tenant_a_id, key_a = await _create_tenant("ASC Alpha", "test-key-alpha-12345")
    _, key_b = await _create_tenant("ASC Beta", "test-key-beta-67890")

    job_a_id = await _create_job(tenant_a_id)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Tenant A CAN read their own job
        resp_own = await client.get(
            f"/api/v1/ingest/jobs/{job_a_id}",
            headers={"X-API-Key": key_a},
        )
        assert resp_own.status_code == 200

        # Tenant B CANNOT read Tenant A's job — gets 404 (not 403, to avoid leaking existence)
        resp_cross = await client.get(
            f"/api/v1/ingest/jobs/{job_a_id}",
            headers={"X-API-Key": key_b},
        )
        assert resp_cross.status_code == 404


# ---------------------------------------------------------------------------
# POST /jobs/{job_id}/retry — cross-tenant retry blocked
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cross_tenant_retry_job_blocked():
    """Tenant B cannot retry Tenant A's failed job."""
    tenant_a_id, key_a = await _create_tenant("ASC Alpha", "test-key-alpha-12345")
    _, key_b = await _create_tenant("ASC Beta", "test-key-beta-67890")

    job_a_id = await _create_job(tenant_a_id, status="failed")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Tenant B tries to retry Tenant A's job — must get 404
        resp_cross = await client.post(
            f"/api/v1/ingest/jobs/{job_a_id}/retry",
            headers={"X-API-Key": key_b},
        )
        assert resp_cross.status_code == 404

        # Verify job status was NOT changed
        async with async_session() as db:
            job = await db.get(IngestionJob, job_a_id)
            assert job.status == "failed"


# ---------------------------------------------------------------------------
# GET /jobs/{job_id}/status (SSE) — cross-tenant observation blocked
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cross_tenant_job_status_sse_blocked():
    """Tenant B cannot observe Tenant A's job status via SSE."""
    tenant_a_id, _ = await _create_tenant("ASC Alpha", "test-key-alpha-12345")
    _, key_b = await _create_tenant("ASC Beta", "test-key-beta-67890")

    job_a_id = await _create_job(tenant_a_id, status="processing")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Tenant B tries to observe Tenant A's job status — must get 404
        resp_cross = await client.get(
            f"/api/v1/ingest/jobs/{job_a_id}/status",
            headers={"X-API-Key": key_b},
        )
        assert resp_cross.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /extraction/{id} — cross-tenant field override blocked
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cross_tenant_extraction_override_blocked():
    """Tenant B cannot modify Tenant A's extraction fields."""
    tenant_a_id, key_a = await _create_tenant("ASC Alpha", "test-key-alpha-12345")
    _, key_b = await _create_tenant("ASC Beta", "test-key-beta-67890")

    job_a_id = await _create_job(tenant_a_id)
    ext_a_id = await _create_extraction(tenant_a_id, job_a_id)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Tenant B tries to override Tenant A's extraction — must get 404
        resp_cross = await client.patch(
            f"/api/v1/extraction/{ext_a_id}",
            headers={"X-API-Key": key_b},
            json={"diagnosis_code": "HACKED"},
        )
        assert resp_cross.status_code == 404

        # Verify Tenant A's data was NOT modified
        async with async_session() as db:
            ext_check = await db.get(ExtractionResult, ext_a_id)
            assert ext_check.diagnosis_code == "M17.11"

        # Tenant A CAN modify their own extraction
        resp_own = await client.patch(
            f"/api/v1/extraction/{ext_a_id}",
            headers={"X-API-Key": key_a},
            json={"diagnosis_code": "M17.12"},
        )
        assert resp_own.status_code == 200
        assert "diagnosis_code" in resp_own.json()["fields_overridden"]


# ---------------------------------------------------------------------------
# PATCH /extraction/{id}/outcome — cross-tenant outcome update blocked
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cross_tenant_outcome_update_blocked():
    """Tenant B cannot update Tenant A's extraction outcome."""
    tenant_a_id, _ = await _create_tenant("ASC Alpha", "test-key-alpha-12345")
    _, key_b = await _create_tenant("ASC Beta", "test-key-beta-67890")

    job_a_id = await _create_job(tenant_a_id)
    ext_a_id = await _create_extraction(tenant_a_id, job_a_id)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Tenant B tries to change outcome — must get 404
        resp_cross = await client.patch(
            f"/api/v1/extraction/{ext_a_id}/outcome",
            headers={"X-API-Key": key_b},
            json={"outcome": "approved"},
        )
        assert resp_cross.status_code == 404

        # Verify outcome was NOT modified
        async with async_session() as db:
            ext_check = await db.get(ExtractionResult, ext_a_id)
            assert ext_check.outcome == "pending"


# ---------------------------------------------------------------------------
# GET /extraction/{id}/export/pdf — cross-tenant PDF export blocked
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cross_tenant_pdf_export_blocked():
    """Tenant B cannot export Tenant A's prior auth as PDF."""
    tenant_a_id, key_a = await _create_tenant("ASC Alpha", "test-key-alpha-12345")
    _, key_b = await _create_tenant("ASC Beta", "test-key-beta-67890")

    job_a_id = await _create_job(tenant_a_id)
    ext_a_id = await _create_extraction(tenant_a_id, job_a_id)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Tenant B tries to export Tenant A's PDF — must get 404
        resp_cross = await client.get(
            f"/api/v1/extraction/{ext_a_id}/export/pdf",
            headers={"X-API-Key": key_b},
        )
        assert resp_cross.status_code == 404

        # Tenant A CAN export their own PDF
        resp_own = await client.get(
            f"/api/v1/extraction/{ext_a_id}/export/pdf",
            headers={"X-API-Key": key_a},
        )
        assert resp_own.status_code == 200
        assert resp_own.headers["content-type"] == "application/pdf"


# ---------------------------------------------------------------------------
# Nonexistent resource tests (returns 404, not 500)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_nonexistent_job_returns_404():
    """Requesting a job that doesn't exist returns 404, not 500."""
    _, key_a = await _create_tenant("ASC Alpha", "test-key-alpha-12345")
    fake_id = str(uuid.uuid4())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/api/v1/ingest/jobs/{fake_id}",
            headers={"X-API-Key": key_a},
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_nonexistent_extraction_returns_404():
    """Requesting an extraction that doesn't exist returns 404."""
    _, key_a = await _create_tenant("ASC Alpha", "test-key-alpha-12345")
    fake_id = str(uuid.uuid4())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # PATCH extraction
        resp = await client.patch(
            f"/api/v1/extraction/{fake_id}",
            headers={"X-API-Key": key_a},
            json={"diagnosis_code": "M17.11"},
        )
        assert resp.status_code == 404

        # PATCH outcome
        resp = await client.patch(
            f"/api/v1/extraction/{fake_id}/outcome",
            headers={"X-API-Key": key_a},
            json={"outcome": "approved"},
        )
        assert resp.status_code == 404

        # GET export PDF
        resp = await client.get(
            f"/api/v1/extraction/{fake_id}/export/pdf",
            headers={"X-API-Key": key_a},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Auth boundary tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_api_key_rejected():
    """Non-existent API key returns 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/ingest/jobs",
            headers={"X-API-Key": "completely-fake-key-that-doesnt-exist"},
        )
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_no_api_key_returns_401():
    """Missing API key returns 401 on all protected endpoints."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for endpoint in [
            "/api/v1/ingest/jobs",
            f"/api/v1/ingest/jobs/{uuid.uuid4()}",
            f"/api/v1/extraction/{uuid.uuid4()}/export/pdf",
            "/api/v1/analytics/outcomes",
        ]:
            resp = await client.get(endpoint)
            assert resp.status_code == 401, f"Expected 401 for {endpoint}, got {resp.status_code}"
