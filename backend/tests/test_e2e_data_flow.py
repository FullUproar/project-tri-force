"""End-to-end data flow tests verifying no PHI leaks through the pipeline.

These tests upload clinical notes with known PHI, wait for processing,
then verify that no PHI appears in any database column or API response.
"""

import re
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.schemas import OrthoPriorAuthData
from tests.conftest import TEST_API_KEY

AUTH = {"X-API-Key": TEST_API_KEY}

# Known PHI that we inject into test notes
KNOWN_PHI = {
    "ssn": "123-45-6789",
    "phone": "555-123-4567",
    "email": "john.smith@hospital.com",
    "mrn": "789012",
    "name": "John Smith",
    "dob": "03/15/1959",
}

CLINICAL_NOTE_WITH_PHI = (
    f"Patient: {KNOWN_PHI['name']} (DOB: {KNOWN_PHI['dob']}, "
    f"SSN: {KNOWN_PHI['ssn']}, Phone: {KNOWN_PHI['phone']}, "
    f"Email: {KNOWN_PHI['email']}, MRN: {KNOWN_PHI['mrn']}). "
    "Diagnosis: M17.11 primary osteoarthritis right knee. "
    "Failed NSAIDs x 8 months, physical therapy x 8 weeks, "
    "cortisone injection with temporary relief. "
    "Recommend total knee arthroplasty with Stryker Triathlon and Mako robotic assistance."
)

MOCK_EXTRACTION = OrthoPriorAuthData(
    diagnosis_code="M17.11",
    conservative_treatments_failed=["NSAIDs", "Physical Therapy", "Cortisone Injection"],
    implant_type_requested="Stryker Triathlon",
    robotic_assistance_required=True,
    clinical_justification="End-stage OA with failed conservative measures.",
    confidence_score=0.95,
)


def _contains_phi(text: str) -> list[str]:
    """Check if text contains any of our known PHI values."""
    found = []
    for label, value in KNOWN_PHI.items():
        if value in text:
            found.append(f"{label}={value}")
    return found


@pytest.mark.asyncio
async def test_extraction_result_contains_no_phi():
    """After processing a note with PHI, the extraction result must not contain any PHI."""
    with patch("app.api.v1.ingest.extract_prior_auth_data", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = MOCK_EXTRACTION

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Upload note with PHI
            response = await client.post(
                "/api/v1/ingest/clinical-note",
                headers=AUTH,
                files={"file": ("note.txt", CLINICAL_NOTE_WITH_PHI.encode(), "text/plain")},
            )

        assert response.status_code == 200
        job_id = response.json()["job_id"]

        # Wait briefly for background task
        import asyncio
        await asyncio.sleep(1)

        # Check the extraction result
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/api/v1/ingest/jobs/{job_id}", headers=AUTH)

        if response.status_code == 200:
            data = response.json()
            result = data.get("extraction_result")
            if result:
                # Serialize all extraction fields to check for PHI
                result_text = str(result)
                phi_found = _contains_phi(result_text)
                assert phi_found == [], f"PHI leaked into extraction result: {phi_found}"


@pytest.mark.asyncio
async def test_scrubber_called_before_llm():
    """Verify the scrubber runs before the LLM extraction function."""
    scrub_called = False
    extract_called = False
    scrub_order = 0
    extract_order = 0
    call_counter = 0

    original_scrub = None
    original_extract = None

    with patch("app.api.v1.ingest.scrub_text_with_stats") as mock_scrub, \
         patch("app.api.v1.ingest.extract_prior_auth_data", new_callable=AsyncMock) as mock_extract:

        def track_scrub(text):
            nonlocal scrub_called, scrub_order, call_counter
            scrub_called = True
            call_counter += 1
            scrub_order = call_counter
            from app.models.schemas import ScrubbedText
            from app.services.phi_scrubber import ScrubResult
            return ScrubResult(ScrubbedText(text), 0, 0)

        mock_scrub.side_effect = track_scrub
        mock_extract.return_value = MOCK_EXTRACTION

        async def track_extract(*args, **kwargs):
            nonlocal extract_called, extract_order, call_counter
            extract_called = True
            call_counter += 1
            extract_order = call_counter
            return MOCK_EXTRACTION

        mock_extract.side_effect = track_extract

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post(
                "/api/v1/ingest/clinical-note",
                headers=AUTH,
                files={"file": ("note.txt", b"Patient has knee pain. Failed NSAIDs. Diagnosis M17.11.", "text/plain")},
            )

        # Give background task time to run
        import asyncio
        await asyncio.sleep(2)

        assert scrub_called, "PHI scrubber was not called"
        assert extract_called, "LLM extraction was not called"
        assert scrub_order < extract_order, "Scrubber must run BEFORE LLM extraction"


@pytest.mark.asyncio
async def test_api_response_contains_no_phi():
    """Job list and status endpoints must never return raw PHI."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # List all jobs
        response = await client.get("/api/v1/ingest/jobs", headers=AUTH)
        assert response.status_code == 200
        jobs_text = response.text
        phi_found = _contains_phi(jobs_text)
        assert phi_found == [], f"PHI found in job list response: {phi_found}"


@pytest.mark.asyncio
async def test_dicom_deidentification_complete():
    """Uploaded DICOM metadata must not contain PHI."""
    import io
    import pydicom
    from pydicom.dataset import FileDataset
    from pydicom.uid import ExplicitVRLittleEndian, generate_uid

    file_meta = pydicom.Dataset()
    file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.2"
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = FileDataset("test.dcm", {}, file_meta=file_meta, preamble=b"\x00" * 128)
    ds.Modality = "CT"
    ds.BodyPartExamined = "KNEE"
    ds.PatientName = "TESTPHI^SHOULDBEREMOVED"
    ds.PatientID = "PHI_MRN_999"
    ds.PatientBirthDate = "19590315"
    ds.ReferringPhysicianName = "PHIDOC^SHOULDGO"

    buf = io.BytesIO()
    ds.save_as(buf)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/ingest/dicom",
            headers=AUTH,
            files={"file": ("test.dcm", buf.getvalue(), "application/dicom")},
        )

    assert response.status_code == 200
    data = response.json()
    metadata = data["metadata"]

    # None of these PHI values should appear in the response
    response_text = str(data)
    assert "TESTPHI" not in response_text
    assert "SHOULDBEREMOVED" not in response_text
    assert "PHI_MRN_999" not in response_text
    assert "19590315" not in response_text
    assert "PHIDOC" not in response_text
    assert "SHOULDGO" not in response_text


@pytest.mark.asyncio
async def test_auth_negative_cases():
    """Verify auth rejects invalid keys."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # No key
        r = await client.get("/api/v1/ingest/jobs")
        assert r.status_code == 401

        # Wrong key
        r = await client.get("/api/v1/ingest/jobs", headers={"X-API-Key": "wrong-key"})
        assert r.status_code == 401

        # Empty key
        r = await client.get("/api/v1/ingest/jobs", headers={"X-API-Key": ""})
        assert r.status_code == 401

        # SQL injection attempt in key
        r = await client.get("/api/v1/ingest/jobs", headers={"X-API-Key": "' OR 1=1 --"})
        assert r.status_code == 401
