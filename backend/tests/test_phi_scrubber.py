import pytest

from app.services.phi_scrubber import _regex_scrub


class TestRegexScrub:
    """Test the regex-based PHI scrubbing pass (no Presidio dependency)."""

    def test_redacts_ssn(self):
        text, count = _regex_scrub("Patient SSN: 123-45-6789")
        assert "[REDACTED_SSN]" in text
        assert "123-45-6789" not in text
        assert count >= 1

    def test_redacts_mrn(self):
        text, _ = _regex_scrub("MRN: 789012345")
        assert "[REDACTED_MRN]" in text
        assert "789012345" not in text

    def test_redacts_phone(self):
        text, _ = _regex_scrub("Phone: 555-123-4567")
        assert "[REDACTED_PHONE]" in text
        assert "555-123-4567" not in text

    def test_redacts_phone_dotted(self):
        text, _ = _regex_scrub("Call 555.123.4567")
        assert "[REDACTED_PHONE]" in text

    def test_redacts_email(self):
        text, _ = _regex_scrub("Contact: john.smith@email.com")
        assert "[REDACTED_EMAIL]" in text
        assert "john.smith@email.com" not in text

    def test_redacts_date_mm_dd_yyyy(self):
        text, _ = _regex_scrub("DOB: 03/15/1959")
        assert "03/15/1959" not in text

    def test_redacts_date_written(self):
        text, _ = _regex_scrub("Born on January 15, 1959")
        assert "January 15, 1959" not in text

    def test_redacts_dob_label(self):
        text, _ = _regex_scrub("DOB: 1959-03-15")
        assert "[REDACTED_DOB]" in text

    def test_preserves_clinical_terms(self):
        text, count = _regex_scrub(
            "Diagnosis: M17.11 Primary osteoarthritis right knee. "
            "Treatment: NSAIDs, Physical Therapy > 6 weeks."
        )
        assert "M17.11" in text
        assert "Primary osteoarthritis" in text
        assert "NSAIDs" in text
        assert "Physical Therapy" in text
        assert count == 0

    def test_preserves_icd10_codes(self):
        text, count = _regex_scrub("ICD-10: M17.11, M16.12, M75.11")
        assert "M17.11" in text
        assert "M16.12" in text
        assert "M75.11" in text
        assert count == 0

    def test_preserves_measurements(self):
        text, count = _regex_scrub("Varus deformity of 12 degrees. Pixel spacing: 0.488mm")
        assert "12 degrees" in text
        assert "0.488mm" in text
        assert count == 0

    def test_multiple_phi_in_one_text(self):
        text, count = _regex_scrub(
            "Patient SSN: 123-45-6789, Phone: 555-123-4567, Email: test@test.com"
        )
        assert "123-45-6789" not in text
        assert "555-123-4567" not in text
        assert "test@test.com" not in text
        assert count >= 3

    def test_empty_text(self):
        text, count = _regex_scrub("")
        assert text == ""
        assert count == 0

    def test_text_with_no_phi(self):
        clinical_text = (
            "The patient presents with end-stage osteoarthritis of the right knee. "
            "Conservative measures including NSAIDs and physical therapy have failed. "
            "Recommend total knee arthroplasty with Mako robotic assistance."
        )
        text, count = _regex_scrub(clinical_text)
        assert text == clinical_text
        assert count == 0

    def test_ssn_at_word_boundary(self):
        # Should not match partial numbers that look like SSNs
        text, count = _regex_scrub("Code 12345-67-890123 is not an SSN")
        assert count == 0

    def test_phone_with_parens(self):
        text, _ = _regex_scrub("Call (555) 123-4567")
        # The parenthesized format should also be caught
        assert "123-4567" not in text


class TestFullClinicalNote:
    """Test scrubbing against realistic clinical notes."""

    def test_scrubs_phi_from_note(self, sample_clinical_note_with_phi):
        text, count = _regex_scrub(sample_clinical_note_with_phi)

        # PHI should be removed
        assert "123-45-6789" not in text  # SSN
        assert "555-123-4567" not in text  # Phone
        assert "john.smith@email.com" not in text  # Email

        # Clinical content should be preserved
        assert "conservative treatment" in text
        assert "NSAIDs" in text
        assert "total knee arthroplasty" in text
        assert count >= 3
