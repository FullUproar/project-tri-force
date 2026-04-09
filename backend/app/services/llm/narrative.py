import asyncio
import time

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

from app.config import settings
from app.core.logging import logger
from app.models.schemas import OrthoPriorAuthData
from app.services.llm.prompts import NARRATIVE_SYSTEM_PROMPT, PAYER_NARRATIVE_SYSTEM_PROMPT

PROMPT_VERSION = "v1.0"
PAYER_PROMPT_VERSION = "v2.0-payer"
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


async def generate_narrative(
    extraction: OrthoPriorAuthData,
    additional_context: str = "",
    payer_name: str | None = None,
    procedure_name: str | None = None,
    payer_criteria: dict | None = None,
) -> tuple[str, str, str]:
    """Generate a payer submission narrative from extraction results.

    Includes a 60-second timeout and up to 2 retries with exponential backoff
    for transient failures.
    """
    # Build payer-specific prompt if payer criteria provided
    system_prompt = None
    prompt_version = PROMPT_VERSION
    if payer_name and payer_criteria:
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

            narrative_text = result.content
            logger.info(
                '{"event": "llm_call", "type": "narrative", "model": "%s", '
                '"latency_ms": %d, "output_chars": %d, "attempt": %d}',
                MODEL_NAME,
                latency_ms,
                len(narrative_text),
                attempt + 1,
            )

            return narrative_text, MODEL_NAME, prompt_version

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

        # Exponential backoff before retry (skip on last attempt)
        if attempt < LLM_MAX_RETRIES:
            backoff = LLM_BACKOFF_BASE ** (attempt + 1)
            await asyncio.sleep(backoff)

    raise RuntimeError(
        f"LLM narrative generation failed after {1 + LLM_MAX_RETRIES} attempts: {last_exception}"
    ) from last_exception
