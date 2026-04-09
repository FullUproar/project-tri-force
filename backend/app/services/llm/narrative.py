import asyncio
import json
import re
import time

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

from app.config import settings
from app.core.logging import logger
from app.models.schemas import OrthoPriorAuthData
from app.services.llm.prompts import (
    CITED_NARRATIVE_SYSTEM_PROMPT,
    NARRATIVE_SYSTEM_PROMPT,
    PAYER_NARRATIVE_SYSTEM_PROMPT,
)

PROMPT_VERSION = "v1.0"
PAYER_PROMPT_VERSION = "v2.0-payer"
CITED_PROMPT_VERSION = "v3.0-cited"
MODEL_NAME = "claude-sonnet-4-20250514"

LLM_TIMEOUT_SECONDS = 60
LLM_MAX_RETRIES = 2
LLM_BACKOFF_BASE = 2  # seconds


def _get_narrative_chain(system_prompt: str | None = None):
    llm = ChatAnthropic(
        model=MODEL_NAME,
        temperature=0.3,
        api_key=settings.anthropic_api_key.get_secret_value(),
        timeout=LLM_TIMEOUT_SECONDS,
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt or NARRATIVE_SYSTEM_PROMPT),
        ("human", """Generate a payer submission narrative for the following clinical data:

Diagnosis Code: {diagnosis_code}
Conservative Treatments Failed: {treatments}
Implant Requested: {implant}
Robotic Assistance Required: {robotic}
Clinical Justification: {justification}

Additional Context (if available):
{additional_context}"""),
    ])

    return prompt | llm


def _parse_citations_from_response(raw_text: str) -> tuple[str, list[dict]]:
    """Extract narrative text and citations JSON from LLM response.

    The LLM outputs the narrative followed by a ```json block with citations.
    Returns (clean_narrative_text, citations_list).
    """
    # Try to find JSON block at end of response
    json_match = re.search(r"```json\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
    if json_match:
        narrative_text = raw_text[:json_match.start()].strip()
        try:
            citation_data = json.loads(json_match.group(1))
            citations = citation_data.get("citations", [])
            return narrative_text, citations
        except json.JSONDecodeError:
            logger.warning("Failed to parse citations JSON from LLM response")
            return narrative_text, []

    # Fallback: try to find JSON object without code fences
    json_match = re.search(r'(\{"citations"\s*:\s*\[.*?\]\s*\})', raw_text, re.DOTALL)
    if json_match:
        narrative_text = raw_text[:json_match.start()].strip()
        try:
            citation_data = json.loads(json_match.group(1))
            return narrative_text, citation_data.get("citations", [])
        except json.JSONDecodeError:
            pass

    # No citations found — return full text
    return raw_text.strip(), []


async def generate_narrative(
    extraction: OrthoPriorAuthData,
    additional_context: str = "",
    payer_name: str | None = None,
    procedure_name: str | None = None,
    payer_criteria: dict | None = None,
    policy_chunks: list | None = None,
) -> tuple[str, str, str, list[dict]]:
    """Generate a payer submission narrative from extraction results.

    Returns (narrative_text, model_used, prompt_version, citations).
    Citations is a list of dicts with marker, claim, source_index, source_type.
    Empty list if no citations requested.

    Includes a 60-second timeout and up to 2 retries with exponential backoff.
    """
    system_prompt = None
    prompt_version = PROMPT_VERSION
    use_citations = False

    if payer_name and policy_chunks:
        # Full cited mode: RAG context + citation markers
        from app.services.llm.prompts import build_numbered_sources, build_payer_criteria_section

        clinical_summary = (
            f"Diagnosis: {extraction.diagnosis_code}. "
            f"Treatments failed: {', '.join(extraction.conservative_treatments_failed)}. "
            f"Implant: {extraction.implant_type_requested}. "
            f"Justification: {extraction.clinical_justification}"
        )
        numbered_sources = build_numbered_sources(policy_chunks, clinical_summary)
        criteria_section = build_payer_criteria_section(payer_criteria or {})

        system_prompt = CITED_NARRATIVE_SYSTEM_PROMPT.format(
            payer_name=payer_name,
            procedure_name=procedure_name or "the requested procedure",
            numbered_sources=numbered_sources,
            payer_criteria_section=criteria_section,
        )
        prompt_version = CITED_PROMPT_VERSION
        use_citations = True

    elif payer_name and payer_criteria:
        # Payer-specific without chunks (no citations)
        from app.services.llm.prompts import build_payer_criteria_section
        criteria_section = build_payer_criteria_section(payer_criteria)
        system_prompt = PAYER_NARRATIVE_SYSTEM_PROMPT.format(
            payer_name=payer_name,
            procedure_name=procedure_name or "the requested procedure",
            payer_criteria_section=criteria_section,
        )
        prompt_version = PAYER_PROMPT_VERSION

    chain = _get_narrative_chain(system_prompt)
    invoke_args = {
        "diagnosis_code": extraction.diagnosis_code,
        "treatments": ", ".join(extraction.conservative_treatments_failed),
        "implant": extraction.implant_type_requested,
        "robotic": "Yes" if extraction.robotic_assistance_required else "No",
        "justification": extraction.clinical_justification,
        "additional_context": additional_context or "None provided",
    }
    last_exception = None

    for attempt in range(1 + LLM_MAX_RETRIES):
        try:
            start = time.monotonic()
            result = await asyncio.wait_for(
                chain.ainvoke(invoke_args),
                timeout=LLM_TIMEOUT_SECONDS,
            )
            latency_ms = round((time.monotonic() - start) * 1000)

            raw_text = result.content

            if use_citations:
                narrative_text, citations = _parse_citations_from_response(raw_text)
            else:
                narrative_text = raw_text
                citations = []

            logger.info(
                '{"event": "llm_call", "type": "narrative", "model": "%s", '
                '"latency_ms": %d, "output_chars": %d, "citations": %d, "attempt": %d}',
                MODEL_NAME,
                latency_ms,
                len(narrative_text),
                len(citations),
                attempt + 1,
            )

            return narrative_text, MODEL_NAME, prompt_version, citations

        except asyncio.TimeoutError:
            last_exception = TimeoutError(
                f"LLM narrative generation timed out after {LLM_TIMEOUT_SECONDS}s (attempt {attempt + 1})"
            )
            logger.warning(
                "LLM narrative timeout on attempt %d/%d",
                attempt + 1,
                1 + LLM_MAX_RETRIES,
            )
        except Exception as e:
            last_exception = e
            logger.warning(
                "LLM narrative failed on attempt %d/%d: %s",
                attempt + 1,
                1 + LLM_MAX_RETRIES,
                str(e),
            )

        if attempt < LLM_MAX_RETRIES:
            backoff = LLM_BACKOFF_BASE ** (attempt + 1)
            await asyncio.sleep(backoff)

    raise RuntimeError(
        f"LLM narrative generation failed after {1 + LLM_MAX_RETRIES} attempts: {last_exception}"
    ) from last_exception
