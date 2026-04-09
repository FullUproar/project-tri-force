"""Integration tests for the upload/ingestion pipeline.

All LLM calls are mocked — no real Anthropic API usage.
Tests use the live Neon database (via app config) since testcontainers
requires Docker-in-Docker which isn't available in all CI environments.
"""

import io
from unittest.mock import AsyncMock, patch

import pydicom
import pytest
from httpx import ASGITransport, AsyncClient
from pydicom.dataset import FileDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

from app.main import app
from app.models.schemas import OrthoPriorAuthData
from tests.conftest import TEST_API_KEY

AUTH = {"X-API-Key": TEST_API_KEY}


def _make_dicom_bytes() -> bytes:
    """Create a minimal valid DICOM file with PHI for testing."""
    file_meta = pydicom.Dataset()
    file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.2"
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = FileDataset("test.dcm", {}, file_meta=file_meta, preamble=b"\x00" * 128)
    ds.Modality = "CT"
    ds.BodyPartExamined = "KNEE"
    ds.StudyDescription = "CT KNEE W/O CONTRAST"
    ds.PatientAge = "067Y"
    ds.Rows = 512
    ds.Columns = 512
    ds.PatientName = "TESTPATIENT^FAKE"
    ds.PatientID = "TESTMRN999"
    ds.PatientBirthDate = "19590115"

    buf = io.BytesIO()
    ds.save_as(buf)
    return buf.getvalue()


MOCK_EXTRACTION = OrthoPriorAuthData(
    diagnosis_code="M17.11",
    conservative_treatments_failed=["NSAIDs", "Physical Therapy"],
    implant_type_requested="Stryker Triathlon",
    robotic_assistance_required=True,
    clinical_justification="End-stage OA with failed conservative treatment.",
    confidence_score=0.92,
)


# --- Auth Tests ---


@pytest.mark.asyncio
async def test_api_returns_401_without_key():
    """All /api/v1 endpoints should return 401 without X-API-Key."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/ingest/jobs/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_health_requires_no_auth():
    """Health endpoint should work without API key."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200


# --- DICOM Ingestion Tests ---


@pytest.mark.asyncio
async def test_upload_dicom_returns_200():
    """DICOM upload should return 200 with metadata and job_id."""
    dicom_bytes = _make_dicom_bytes()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/ingest/dicom",
            headers=AUTH,
            files={"file": ("test.dcm", dicom_bytes, "application/dicom")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["job_id"]
    assert data["metadata"]["Modality"] == "CT"
    assert data["metadata"]["BodyPartExamined"] == "KNEE"


@pytest.mark.asyncio
async def test_dicom_upload_strips_phi():
    """DICOM response should not contain any PHI."""
    dicom_bytes = _make_dicom_bytes()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/ingest/dicom",
            headers=AUTH,
            files={"file": ("test.dcm", dicom_bytes, "application/dicom")},
        )

    data = response.json()
    metadata = data["metadata"]
    assert "PatientName" not in metadata
    assert "PatientID" not in metadata
    assert "PatientBirthDate" not in metadata


@pytest.mark.asyncio
async def test_upload_invalid_dicom_returns_400():
    """Uploading a non-DICOM file with .dcm extension should return 400."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/ingest/dicom",
            headers=AUTH,
            files={"file": ("fake.dcm", b"not a dicom file", "application/dicom")},
        )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_wrong_extension_returns_400():
    """Uploading a .txt file to the DICOM endpoint should return 400."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/ingest/dicom",
            headers=AUTH,
            files={"file": ("note.txt", b"some text", "text/plain")},
        )

    assert response.status_code == 400


# --- Clinical Note Ingestion Tests ---


@pytest.mark.asyncio
async def test_upload_clinical_note_returns_processing():
    """Clinical note upload should return job_id with processing status."""
    with patch("app.api.v1.ingest._process_text_ingestion", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/ingest/clinical-note",
                headers=AUTH,
                files={"file": ("note.txt", b"Patient has knee pain. Failed NSAIDs.", "text/plain")},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processing"
    assert data["job_id"]


# --- Robotic Report Ingestion Tests ---


@pytest.mark.asyncio
async def test_upload_pdf_returns_processing():
    """PDF robotic report upload should return job_id with processing status."""
    with open("tests/fixtures/test_report.pdf", "rb") as f:
        pdf_bytes = f.read()

    with patch("app.api.v1.ingest._process_text_ingestion", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/ingest/robotic-report",
                headers=AUTH,
                files={"file": ("report.pdf", pdf_bytes, "application/pdf")},
            )

    # Our test PDF has no extractable text, so it should return 400
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_non_pdf_to_robotic_returns_400():
    """Uploading a non-PDF to the robotic report endpoint should return 400."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/ingest/robotic-report",
            headers=AUTH,
            files={"file": ("report.txt", b"not a pdf", "text/plain")},
        )

    assert response.status_code == 400


# --- Job Status Tests ---


@pytest.mark.asyncio
async def test_job_not_found_returns_404():
    """Requesting a non-existent job should return 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/ingest/jobs/00000000-0000-0000-0000-000000000000",
            headers=AUTH,
        )

    assert response.status_code == 404


# --- LLM Extraction Tests (mocked) ---


@pytest.mark.asyncio
async def test_extraction_chain_mocked():
    """Verify extraction service returns OrthoPriorAuthData when LLM is mocked."""
    from app.models.schemas import ScrubbedText

    with patch("app.services.llm.extraction._get_extraction_chain") as mock_chain:
        mock_chain.return_value.ainvoke = AsyncMock(return_value=MOCK_EXTRACTION)

        from app.services.llm.extraction import extract_prior_auth_data

        result = await extract_prior_auth_data(
            ScrubbedText("Patient has end-stage OA right knee. Failed NSAIDs and PT.")
        )

    assert result.diagnosis_code == "M17.11"
    assert "NSAIDs" in result.conservative_treatments_failed
    assert result.robotic_assistance_required is True
    assert result.confidence_score == 0.92


# --- Narrative Generation Tests (mocked) ---


@pytest.mark.asyncio
async def test_narrative_generation_mocked():
    """Verify narrative service returns text when LLM is mocked."""
    mock_response = type("MockResponse", (), {"content": "This letter serves as clinical justification..."})()

    with patch("app.services.llm.narrative._get_narrative_chain") as mock_chain:
        mock_chain.return_value.ainvoke = AsyncMock(return_value=mock_response)

        from app.services.llm.narrative import generate_narrative

        text, model, version, citations = await generate_narrative(MOCK_EXTRACTION)

    assert "clinical justification" in text
    assert model == "claude-sonnet-4-20250514"
    assert version == "v1.0"
    assert isinstance(citations, list)
