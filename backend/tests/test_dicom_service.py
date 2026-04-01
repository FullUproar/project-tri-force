from app.services.dicom_service import extract_metadata, deidentify, parse_dicom

import pydicom
from io import BytesIO


class TestExtractMetadata:
    def test_extracts_core_fields(self, sample_dicom_bytes):
        ds = pydicom.dcmread(BytesIO(sample_dicom_bytes))
        metadata = extract_metadata(ds)

        assert metadata["Modality"] == "CT"
        assert metadata["BodyPartExamined"] == "KNEE"
        assert metadata["PatientAge"] == "067Y"
        assert metadata["StudyDescription"] == "CT KNEE W/O CONTRAST"
        assert metadata["ImageDimensions"] == [512, 512]
        assert metadata["PixelSpacing"] == [0.488, 0.488]
        assert metadata["SliceThickness"] == 1.25

    def test_no_phi_in_metadata(self, sample_dicom_bytes):
        ds = pydicom.dcmread(BytesIO(sample_dicom_bytes))
        metadata = extract_metadata(ds)

        # Metadata should NOT contain PHI fields
        assert "PatientName" not in metadata
        assert "PatientID" not in metadata
        assert "PatientBirthDate" not in metadata


class TestDeidentify:
    def test_removes_patient_name(self, sample_dicom_bytes):
        ds = pydicom.dcmread(BytesIO(sample_dicom_bytes))
        assert hasattr(ds, "PatientName")

        ds = deidentify(ds)
        assert not hasattr(ds, "PatientName")

    def test_removes_patient_id(self, sample_dicom_bytes):
        ds = pydicom.dcmread(BytesIO(sample_dicom_bytes))
        ds = deidentify(ds)
        assert not hasattr(ds, "PatientID")

    def test_removes_institution_name(self, sample_dicom_bytes):
        ds = pydicom.dcmread(BytesIO(sample_dicom_bytes))
        ds = deidentify(ds)
        assert not hasattr(ds, "InstitutionName")

    def test_removes_referring_physician(self, sample_dicom_bytes):
        ds = pydicom.dcmread(BytesIO(sample_dicom_bytes))
        ds = deidentify(ds)
        assert not hasattr(ds, "ReferringPhysicianName")

    def test_removes_person_name_vr_tags(self, sample_dicom_bytes):
        ds = pydicom.dcmread(BytesIO(sample_dicom_bytes))
        ds = deidentify(ds)

        # No remaining PersonName (PN) VR elements
        for elem in ds:
            assert elem.VR != "PN", f"Found unremoved PN tag: {elem.tag}"

    def test_preserves_clinical_data(self, sample_dicom_bytes):
        ds = pydicom.dcmread(BytesIO(sample_dicom_bytes))
        ds = deidentify(ds)

        assert ds.Modality == "CT"
        assert ds.BodyPartExamined == "KNEE"


class TestParseDicom:
    def test_returns_metadata_and_bytes(self, sample_dicom_bytes):
        metadata, deidentified_bytes = parse_dicom(sample_dicom_bytes)

        assert isinstance(metadata, dict)
        assert isinstance(deidentified_bytes, bytes)
        assert len(deidentified_bytes) > 0

    def test_deidentified_bytes_have_no_phi(self, sample_dicom_bytes):
        _, deidentified_bytes = parse_dicom(sample_dicom_bytes)

        # Read back the de-identified DICOM
        ds = pydicom.dcmread(BytesIO(deidentified_bytes))
        assert not hasattr(ds, "PatientName")
        assert not hasattr(ds, "PatientID")
        assert not hasattr(ds, "PatientBirthDate")
