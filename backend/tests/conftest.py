import io
import uuid

import pydicom
import pytest
import pytest_asyncio
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid


def _patch_engine():
    """Patch the DB engine to use NullPool before any test imports the app."""
    from sqlalchemy.pool import NullPool
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

    import app.core.db as db_module
    from app.config import settings

    db_module.engine = create_async_engine(
        settings.database_url,
        echo=False,
        poolclass=NullPool,
    )
    db_module.async_session = async_sessionmaker(
        db_module.engine, class_=AsyncSession, expire_on_commit=False
    )


_patch_engine()

TEST_API_KEY = "test-key-for-pytest"


@pytest.fixture(scope="session", autouse=True)
def _set_test_api_key():
    """Set a known API key for tests."""
    from app.config import settings
    from pydantic import SecretStr

    object.__setattr__(settings, "api_key", SecretStr(TEST_API_KEY))


@pytest.fixture
def sample_dicom_bytes() -> bytes:
    """Create a minimal valid DICOM file in memory for testing."""
    file_meta = pydicom.Dataset()
    file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.2"  # CT Image
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = FileDataset("test.dcm", {}, file_meta=file_meta, preamble=b"\x00" * 128)

    # Clinical metadata
    ds.Modality = "CT"
    ds.BodyPartExamined = "KNEE"
    ds.StudyDescription = "CT KNEE W/O CONTRAST"
    ds.PatientAge = "067Y"
    ds.Rows = 512
    ds.Columns = 512
    ds.PixelSpacing = [0.488, 0.488]
    ds.SliceThickness = 1.25

    # PHI that should be removed
    ds.PatientName = "DOE^JOHN"
    ds.PatientID = "MRN123456"
    ds.PatientBirthDate = "19590115"
    ds.InstitutionName = "Springfield General Hospital"
    ds.ReferringPhysicianName = "SMITH^JANE^DR"

    buffer = io.BytesIO()
    ds.save_as(buffer)
    return buffer.getvalue()


@pytest.fixture
def sample_clinical_note() -> str:
    """A synthetic clinical note with known entities for extraction testing."""
    return """
ORTHOPAEDIC CONSULTATION NOTE

Patient presents with severe right knee pain consistent with end-stage osteoarthritis.
Weight-bearing AP and lateral radiographs demonstrate bone-on-bone changes with
complete loss of medial joint space, subchondral sclerosis, and osteophyte formation.

DIAGNOSIS: Primary osteoarthritis, right knee (ICD-10: M17.11)

CONSERVATIVE TREATMENT HISTORY:
- NSAIDs (Meloxicam 15mg daily) x 8 months - inadequate pain relief
- Physical therapy (3x/week for 8 weeks) - completed without significant improvement
- Cortisone injection (40mg triamcinolone) - temporary relief lasting 3 weeks
- Hyaluronic acid viscosupplementation (Synvisc-One) - no benefit

The patient has failed all reasonable conservative measures. Given the severity of
radiographic findings and functional limitation, I recommend proceeding with
right total knee arthroplasty using the Stryker Triathlon Total Knee System with
Mako robotic-assisted surgical technique.

The use of Mako robotic assistance is indicated to optimize implant positioning
and soft tissue balance, which is particularly important given the patient's
significant varus deformity of 12 degrees.
"""


@pytest.fixture
def sample_clinical_note_with_phi() -> str:
    """A clinical note containing PHI that must be scrubbed."""
    return """
Patient: John Smith (DOB: 03/15/1959)
MRN: 789012
SSN: 123-45-6789
Phone: 555-123-4567
Email: john.smith@email.com
Address: 123 Main Street, Springfield, IL 62701

Dr. Jane Wilson referred this 67-year-old male for evaluation of right knee pain.
Patient has failed conservative treatment including NSAIDs and physical therapy.
Recommend total knee arthroplasty.
"""
