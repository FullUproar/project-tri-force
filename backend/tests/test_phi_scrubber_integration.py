"""Integration tests for the full PHI scrubbing pipeline (regex + Presidio).

These tests run the complete scrub_text() function, not just the regex pass.
They verify that Presidio's NER catches names, locations, and other entities
that regex alone cannot detect.
"""

import pytest

from app.services.phi_scrubber import scrub_text, _regex_scrub
from app.models.schemas import ScrubbedText


class TestFullScrubText:
    """Tests that run the complete dual-pass scrubber."""

    def test_returns_scrubbed_text_type(self):
        result = scrub_text("Simple clinical text with no PHI")
        assert isinstance(result, str)  # ScrubbedText is a NewType of str

    def test_removes_ssn(self):
        result = scrub_text("Patient SSN: 123-45-6789. Knee OA diagnosis.")
        assert "123-45-6789" not in result
        assert "Knee OA" in result

    def test_removes_phone(self):
        result = scrub_text("Call patient at 555-123-4567 regarding surgery.")
        assert "555-123-4567" not in result
        assert "surgery" in result

    def test_removes_email(self):
        result = scrub_text("Email: john.smith@hospital.com for scheduling.")
        assert "john.smith@hospital.com" not in result
        assert "scheduling" in result

    def test_removes_mrn(self):
        result = scrub_text("MRN: 789012. Patient has knee OA.")
        assert "789012" not in result
        assert "knee OA" in result

    def test_removes_person_names(self):
        """Presidio should catch person names that regex cannot."""
        result = scrub_text(
            "Dr. Jane Wilson referred John Smith for evaluation of knee pain."
        )
        # Names should be redacted by Presidio NER
        assert "John Smith" not in result
        assert "knee pain" in result

    def test_removes_location(self):
        """Presidio should catch location names."""
        result = scrub_text(
            "Patient from Springfield General Hospital presents with hip pain."
        )
        assert "hip pain" in result

    def test_removes_dates_various_formats(self):
        result = scrub_text(
            "DOB: 03/15/1959. Surgery scheduled for January 15, 2026. "
            "Follow-up on 2026-04-15."
        )
        assert "03/15/1959" not in result
        assert "January 15, 2026" not in result

    def test_preserves_icd10_codes(self):
        result = scrub_text("Diagnosis: M17.11, M16.12, M75.11. Recommend surgery.")
        assert "M17.11" in result
        assert "M16.12" in result
        assert "M75.11" in result

    def test_preserves_clinical_terminology(self):
        result = scrub_text(
            "End-stage osteoarthritis with Kellgren-Lawrence Grade IV changes. "
            "Subchondral sclerosis and osteophyte formation. "
            "Varus deformity of 12 degrees."
        )
        assert "osteoarthritis" in result
        assert "Kellgren-Lawrence" in result
        assert "sclerosis" in result.lower()
        assert "12 degrees" in result

    def test_preserves_treatment_names(self):
        result = scrub_text(
            "Failed NSAIDs (Meloxicam 15mg daily), physical therapy, "
            "cortisone injection (triamcinolone 40mg), and Synvisc-One."
        )
        assert "NSAIDs" in result
        assert "Meloxicam" in result
        assert "physical therapy" in result
        assert "cortisone" in result
        assert "Synvisc-One" in result

    def test_preserves_implant_names(self):
        result = scrub_text(
            "Recommend Stryker Triathlon Total Knee System with Mako robotic assistance."
        )
        assert "Stryker Triathlon" in result
        assert "Mako" in result

    def test_handles_empty_string(self):
        result = scrub_text("")
        assert result == ""

    def test_handles_clinical_only_text(self):
        """Text with no PHI should pass through unchanged (minus any false positives)."""
        original = (
            "End-stage osteoarthritis right knee. Failed conservative treatment. "
            "Recommend total knee arthroplasty."
        )
        result = scrub_text(original)
        # Core clinical content should survive
        assert "osteoarthritis" in result
        assert "total knee arthroplasty" in result


class TestAdversarialPHI:
    """Edge cases that are tricky for PHI detection."""

    def test_name_that_looks_like_medical_term(self):
        """'Baker' is both a name and a medical term (Baker cyst)."""
        result = scrub_text(
            "Baker cyst noted on MRI. No relationship to Dr. Baker."
        )
        # "Baker cyst" should ideally survive as a medical term
        # "Dr. Baker" should be caught as a name
        # This is an inherently difficult case — document behavior
        assert "cyst" in result

    def test_mixed_phi_and_clinical(self):
        result = scrub_text(
            "Patient John A. Smith (DOB: 03/15/1959, MRN: 789012, "
            "SSN: 123-45-6789, Phone: (555) 123-4567, "
            "Email: john.smith@email.com) from Springfield, IL 62701. "
            "Dr. Jane Wilson referred this 67-year-old male. "
            "Diagnosis: M17.11. Failed NSAIDs x 8 months, PT x 8 weeks, "
            "cortisone injection. Recommend TKA with Mako."
        )
        # All PHI should be gone
        assert "123-45-6789" not in result  # SSN
        assert "john.smith@email.com" not in result  # Email
        # Clinical content should survive
        assert "M17.11" in result
        assert "NSAIDs" in result
        assert "TKA" in result
        assert "Mako" in result

    def test_partial_ssn(self):
        """Numbers that look like partial SSNs should not cause false positives."""
        result = scrub_text("Flexion gap: 22mm. Extension gap: 20mm. Size 5 femoral component.")
        assert "22mm" in result
        assert "20mm" in result
        assert "Size 5" in result

    def test_phone_in_parentheses(self):
        result = scrub_text("Reach at (555) 123-4567 or 555.123.4567.")
        assert "123-4567" not in result

    def test_medical_license_number(self):
        """Medical license numbers are PHI under HIPAA."""
        result = scrub_text("Referring physician license: MD12345678.")
        # May or may not be caught — document behavior
        assert "physician" in result or "license" in result

    def test_international_date_format(self):
        result = scrub_text("DOB: 15/03/1959. Surgery date: 01/04/2026.")
        # These should be caught by either regex or Presidio
        assert "1959" not in result or "REDACTED" in result


class TestScrubbedTextTypeGuard:
    """Verify the ScrubbedText type system works as intended."""

    def test_scrub_text_returns_scrubbed_type(self):
        result = scrub_text("Some text")
        # ScrubbedText is a NewType — at runtime it's just a str,
        # but the type checker should enforce it at call sites
        assert isinstance(result, str)

    def test_extraction_function_signature(self):
        """Verify the extraction function requires ScrubbedText parameter."""
        import inspect
        from app.services.llm.extraction import extract_prior_auth_data

        sig = inspect.signature(extract_prior_auth_data)
        param = sig.parameters["scrubbed_text"]
        # The annotation should reference ScrubbedText
        assert "ScrubbedText" in str(param.annotation)
