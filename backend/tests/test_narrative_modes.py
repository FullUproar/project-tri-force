"""Tests for payer-specific and cited narrative generation modes (LLM mocked).

Covers the three narrative modes:
  - v1.0 generic (already tested in test_upload_pipeline.py)
  - v2.0-payer: payer-specific without citations
  - v3.0-cited: RAG-augmented with inline citation markers
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.models.schemas import OrthoPriorAuthData

MOCK_EXTRACTION = OrthoPriorAuthData(
    diagnosis_code="M17.11",
    conservative_treatments_failed=["NSAIDs", "Physical Therapy", "Cortisone injection"],
    implant_type_requested="Stryker Triathlon",
    robotic_assistance_required=True,
    clinical_justification="End-stage OA right knee with bone-on-bone changes and failed conservative treatment.",
    confidence_score=0.92,
)

PAYER_CRITERIA = {
    "conservative_treatment_min_months": 3,
    "required_modalities": ["NSAIDs", "Physical Therapy"],
    "imaging_required": "Weight-bearing AP and lateral radiographs",
    "imaging_max_age_months": 6,
    "functional_impairment_required": True,
    "submission_portal": "https://provider.uhc.com",
}


# ---------------------------------------------------------------------------
# v2.0-payer: Payer-specific narrative (no citations)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_payer_specific_narrative_uses_payer_prompt():
    """Payer-specific mode uses v2.0-payer prompt and returns the correct version."""
    mock_response = type("MockResponse", (), {
        "content": "This letter is submitted to UnitedHealthcare to request prior authorization for total knee arthroplasty..."
    })()

    captured_system_prompt = {}

    original_get_chain = None

    def mock_get_chain(system_prompt=None):
        captured_system_prompt["value"] = system_prompt
        chain = AsyncMock()
        chain.ainvoke = AsyncMock(return_value=mock_response)
        return chain

    with patch("app.services.llm.narrative._get_narrative_chain", side_effect=mock_get_chain):
        from app.services.llm.narrative import generate_narrative

        text, model, version, citations = await generate_narrative(
            MOCK_EXTRACTION,
            payer_name="UnitedHealthcare",
            procedure_name="Total Knee Replacement",
            payer_criteria=PAYER_CRITERIA,
        )

    assert version == "v2.0-payer"
    assert "UnitedHealthcare" in text
    assert isinstance(citations, list)
    assert len(citations) == 0  # No citations in payer-specific mode without chunks

    # Verify payer-specific system prompt was used
    assert captured_system_prompt["value"] is not None
    assert "UnitedHealthcare" in captured_system_prompt["value"]
    assert "conservative_treatment" in captured_system_prompt["value"].lower() or "NSAIDs" in captured_system_prompt["value"]


# ---------------------------------------------------------------------------
# v3.0-cited: RAG-augmented with inline citations
# ---------------------------------------------------------------------------


class MockChunk:
    """Simulates a PolicyChunk object for RAG context."""
    def __init__(self, section_title: str, content: str):
        self.section_title = section_title
        self.content = content


@pytest.mark.asyncio
async def test_cited_narrative_parses_citations():
    """Cited mode parses citation markers and JSON block from LLM response."""
    narrative_with_citations = (
        "The patient presents with end-stage osteoarthritis of the right knee [0]. "
        "UnitedHealthcare requires a minimum of 3 months of conservative treatment [1], "
        "which the patient has exceeded with 8 months of NSAIDs and physical therapy [0]. "
        "Weight-bearing radiographs demonstrate bone-on-bone changes [2].\n\n"
        "```json\n"
        '{"citations": ['
        '{"marker": "0", "claim": "Patient clinical data supports diagnosis", "source_index": 0, "source_type": "clinical_note"},'
        '{"marker": "1", "claim": "UHC requires 3 months conservative treatment", "source_index": 1, "source_type": "payer_policy"},'
        '{"marker": "2", "claim": "Imaging requirements per UHC policy", "source_index": 2, "source_type": "payer_policy"}'
        "]}\n"
        "```"
    )

    mock_response = type("MockResponse", (), {"content": narrative_with_citations})()

    def mock_get_chain(system_prompt=None):
        chain = AsyncMock()
        chain.ainvoke = AsyncMock(return_value=mock_response)
        return chain

    policy_chunks = [
        MockChunk("Conservative Treatment Requirements", "Patient must complete minimum 3 months of conservative treatment including NSAIDs and physical therapy."),
        MockChunk("Imaging Requirements", "Weight-bearing AP and lateral radiographs within 6 months of request date."),
    ]

    with patch("app.services.llm.narrative._get_narrative_chain", side_effect=mock_get_chain):
        from app.services.llm.narrative import generate_narrative

        text, model, version, citations = await generate_narrative(
            MOCK_EXTRACTION,
            payer_name="UnitedHealthcare",
            procedure_name="Total Knee Replacement",
            payer_criteria=PAYER_CRITERIA,
            policy_chunks=policy_chunks,
        )

    assert version == "v3.0-cited"
    assert len(citations) == 3
    assert citations[0]["marker"] == "0"
    assert citations[0]["source_type"] == "clinical_note"
    assert citations[1]["source_type"] == "payer_policy"

    # Narrative text should not contain the JSON block
    assert "```json" not in text
    assert "source_index" not in text


@pytest.mark.asyncio
async def test_cited_narrative_handles_missing_json():
    """Cited mode handles LLM response with no JSON citations block gracefully."""
    mock_response = type("MockResponse", (), {
        "content": "The patient has end-stage OA [1] and requires total knee arthroplasty."
    })()

    def mock_get_chain(system_prompt=None):
        chain = AsyncMock()
        chain.ainvoke = AsyncMock(return_value=mock_response)
        return chain

    policy_chunks = [
        MockChunk("Overview", "Total knee replacement policy overview."),
    ]

    with patch("app.services.llm.narrative._get_narrative_chain", side_effect=mock_get_chain):
        from app.services.llm.narrative import generate_narrative

        text, model, version, citations = await generate_narrative(
            MOCK_EXTRACTION,
            payer_name="Aetna",
            procedure_name="Total Knee Replacement",
            payer_criteria=PAYER_CRITERIA,
            policy_chunks=policy_chunks,
        )

    assert version == "v3.0-cited"
    assert len(citations) == 0  # Graceful fallback — no crash
    assert "end-stage OA" in text


# ---------------------------------------------------------------------------
# Generic mode falls through when no payer info provided
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generic_narrative_when_no_payer():
    """Without payer info, generates v1.0 generic narrative."""
    mock_response = type("MockResponse", (), {
        "content": "This letter serves as clinical justification for total knee arthroplasty."
    })()

    def mock_get_chain(system_prompt=None):
        chain = AsyncMock()
        chain.ainvoke = AsyncMock(return_value=mock_response)
        return chain

    with patch("app.services.llm.narrative._get_narrative_chain", side_effect=mock_get_chain):
        from app.services.llm.narrative import generate_narrative

        text, model, version, citations = await generate_narrative(MOCK_EXTRACTION)

    assert version == "v1.0"
    assert len(citations) == 0


# ---------------------------------------------------------------------------
# Prompt helper unit tests
# ---------------------------------------------------------------------------


def test_build_payer_criteria_section():
    """build_payer_criteria_section produces readable output from criteria dict."""
    from app.services.llm.prompts import build_payer_criteria_section

    result = build_payer_criteria_section(PAYER_CRITERIA)
    assert "3 months" in result
    assert "NSAIDs" in result
    assert "Physical Therapy" in result
    assert "Weight-bearing" in result
    assert "provider.uhc.com" in result


def test_build_payer_criteria_empty():
    """Empty criteria dict produces fallback message."""
    from app.services.llm.prompts import build_payer_criteria_section

    result = build_payer_criteria_section({})
    assert "No specific criteria" in result


def test_suggest_procedure_from_diagnosis():
    """ICD-10 code prefix maps to correct procedure."""
    from app.services.llm.prompts import suggest_procedure_from_diagnosis

    assert suggest_procedure_from_diagnosis("M17.11") == "Total Knee Replacement"
    assert suggest_procedure_from_diagnosis("M16.12") == "Total Hip Replacement"
    assert suggest_procedure_from_diagnosis("M75.11") == "Rotator Cuff Repair"
    assert suggest_procedure_from_diagnosis("G89.4") == "Spinal Cord Stimulator"
    assert suggest_procedure_from_diagnosis("M54.5") == "Lumbar Fusion"
    assert suggest_procedure_from_diagnosis(None) is None
    assert suggest_procedure_from_diagnosis("Z99.99") is None


def test_build_numbered_sources():
    """build_numbered_sources produces correctly indexed source list."""
    from app.services.llm.prompts import build_numbered_sources

    chunks = [
        MockChunk("Overview", "Policy overview content."),
        MockChunk("Treatment", "Conservative treatment requirements."),
    ]

    result = build_numbered_sources(chunks, "Patient has end-stage OA.")
    assert "[0] CLINICAL DATA:" in result
    assert "[1] PAYER POLICY (Overview):" in result
    assert "[2] PAYER POLICY (Treatment):" in result


def test_build_numbered_sources_no_clinical():
    """Without clinical context, sources start from index 0."""
    from app.services.llm.prompts import build_numbered_sources

    chunks = [MockChunk("Overview", "Content here.")]
    result = build_numbered_sources(chunks)
    assert "[0] PAYER POLICY (Overview):" in result
    assert "CLINICAL DATA" not in result
