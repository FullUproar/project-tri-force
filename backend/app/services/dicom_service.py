from io import BytesIO

import pydicom
from pydicom.dataset import Dataset

from app.core.logging import logger

# DICOM tags that may contain PHI — must be removed before storage or LLM processing
# Based on DICOM Supplement 142 (Clinical Trial De-identification Profile)
PHI_TAGS = [
    "PatientName",
    "PatientID",
    "PatientBirthDate",
    "PatientBirthTime",
    "PatientSex",
    "PatientAge",  # Keep age for metadata, but anonymize in stored file
    "OtherPatientIDs",
    "OtherPatientNames",
    "PatientAddress",
    "PatientTelephoneNumbers",
    "InstitutionName",
    "InstitutionAddress",
    "ReferringPhysicianName",
    "ReferringPhysicianAddress",
    "ReferringPhysicianTelephoneNumbers",
    "PerformingPhysicianName",
    "NameOfPhysiciansReadingStudy",
    "OperatorsName",
    "AccessionNumber",
    "StudyID",
    "RequestingPhysician",
    "ScheduledPerformingPhysicianName",
]

# Tags we extract for metadata (extracted BEFORE de-identification)
METADATA_TAGS = [
    "PatientAge",
    "Modality",
    "BodyPartExamined",
    "StudyDescription",
    "Rows",
    "Columns",
]


def extract_metadata(ds: Dataset) -> dict:
    """Extract clinically relevant metadata from a DICOM dataset."""
    metadata = {}

    for tag_name in METADATA_TAGS:
        if hasattr(ds, tag_name):
            value = getattr(ds, tag_name)
            metadata[tag_name] = str(value) if value is not None else None

    # Extract pixel spacing if available
    if hasattr(ds, "PixelSpacing") and ds.PixelSpacing:
        metadata["PixelSpacing"] = [float(x) for x in ds.PixelSpacing]

    if hasattr(ds, "SliceThickness") and ds.SliceThickness:
        metadata["SliceThickness"] = float(ds.SliceThickness)

    # Image dimensions
    if "Rows" in metadata and "Columns" in metadata:
        metadata["ImageDimensions"] = [
            int(metadata.pop("Rows")),
            int(metadata.pop("Columns")),
        ]

    return metadata


def deidentify(ds: Dataset) -> Dataset:
    """Remove PHI from a DICOM dataset using Safe Harbor method."""
    removed_count = 0

    # Remove known PHI tags
    for tag_name in PHI_TAGS:
        if hasattr(ds, tag_name):
            delattr(ds, tag_name)
            removed_count += 1

    # Also remove any tag with VR of PersonName (PN) — catches vendor-specific PHI
    for elem in list(ds):
        if elem.VR == "PN":
            del ds[elem.tag]
            removed_count += 1

    logger.info("De-identified DICOM: removed %d PHI elements", removed_count)
    return ds


def parse_dicom(file_bytes: bytes) -> tuple[dict, bytes]:
    """Parse a DICOM file, extract metadata, and return de-identified bytes.

    Returns:
        tuple of (metadata_dict, deidentified_file_bytes)
    """
    ds = pydicom.dcmread(BytesIO(file_bytes))

    # Extract metadata BEFORE de-identification (so we get PatientAge etc.)
    metadata = extract_metadata(ds)

    # De-identify
    ds = deidentify(ds)

    # Serialize de-identified DICOM back to bytes
    buffer = BytesIO()
    ds.save_as(buffer)
    deidentified_bytes = buffer.getvalue()

    return metadata, deidentified_bytes
