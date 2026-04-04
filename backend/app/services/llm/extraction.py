import asyncio
import time

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

from app.config import settings
from app.core.logging import logger
from app.models.schemas import OrthoPriorAuthData, ScrubbedText
from app.services.llm.prompts import EXTRACTION_SYSTEM_PROMPT

LLM_TIMEOUT_SECONDS = 60
LLM_MAX_RETRIES = 2
LLM_BACKOFF_BASE = 2  # seconds


def _get_extraction_chain():
    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        temperature=0,
        api_key=settings.anthropic_api_key.get_secret_value(),
        timeout=LLM_TIMEOUT_SECONDS,
    )
    structured_llm = llm.with_structured_output(OrthoPriorAuthData)

    prompt = ChatPromptTemplate.from_messages([
        ("system", EXTRACTION_SYSTEM_PROMPT),
        ("human", "Extract the prior authorization data from this clinical text:\n\n{text}"),
    ])

    return prompt | structured_llm


async def extract_prior_auth_data(scrubbed_text: ScrubbedText) -> OrthoPriorAuthData:
    """Extract structured OrthoPriorAuthData from scrubbed clinical text.

    Includes a 60-second timeout and up to 2 retries with exponential backoff
    for transient failures.
    """
    chain = _get_extraction_chain()
    last_exception = None

    for attempt in range(1 + LLM_MAX_RETRIES):
        try:
            start = time.monotonic()
            result = await asyncio.wait_for(
                chain.ainvoke({"text": str(scrubbed_text)}),
                timeout=LLM_TIMEOUT_SECONDS,
            )
            latency_ms = round((time.monotonic() - start) * 1000)

            logger.info(
                '{"event": "llm_call", "type": "extraction", "model": "claude-sonnet-4-20250514", '
                '"latency_ms": %d, "diagnosis": "%s", "confidence": %.2f, "attempt": %d}',
                latency_ms,
                result.diagnosis_code,
                result.confidence_score,
                attempt + 1,
            )
            return result

        except asyncio.TimeoutError:
            last_exception = TimeoutError(
                f"LLM extraction timed out after {LLM_TIMEOUT_SECONDS}s (attempt {attempt + 1})"
            )
            logger.warning(
                "LLM extraction timeout on attempt %d/%d",
                attempt + 1,
                1 + LLM_MAX_RETRIES,
            )
        except Exception as e:
            last_exception = e
            logger.warning(
                "LLM extraction failed on attempt %d/%d: %s",
                attempt + 1,
                1 + LLM_MAX_RETRIES,
                str(e),
            )

        # Exponential backoff before retry (skip on last attempt)
        if attempt < LLM_MAX_RETRIES:
            backoff = LLM_BACKOFF_BASE ** (attempt + 1)
            await asyncio.sleep(backoff)

    raise RuntimeError(
        f"LLM extraction failed after {1 + LLM_MAX_RETRIES} attempts: {last_exception}"
    ) from last_exception
