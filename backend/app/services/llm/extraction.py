import time

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

from app.config import settings
from app.core.logging import logger
from app.models.schemas import OrthoPriorAuthData, ScrubbedText
from app.services.llm.prompts import EXTRACTION_SYSTEM_PROMPT


def _get_extraction_chain():
    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        temperature=0,
        api_key=settings.anthropic_api_key.get_secret_value(),
    )
    structured_llm = llm.with_structured_output(OrthoPriorAuthData)

    prompt = ChatPromptTemplate.from_messages([
        ("system", EXTRACTION_SYSTEM_PROMPT),
        ("human", "Extract the prior authorization data from this clinical text:\n\n{text}"),
    ])

    return prompt | structured_llm


async def extract_prior_auth_data(scrubbed_text: ScrubbedText) -> OrthoPriorAuthData:
    """Extract structured OrthoPriorAuthData from scrubbed clinical text."""
    chain = _get_extraction_chain()

    start = time.monotonic()
    result = await chain.ainvoke({"text": str(scrubbed_text)})
    latency_ms = round((time.monotonic() - start) * 1000)

    logger.info(
        '{"event": "llm_call", "type": "extraction", "model": "claude-sonnet-4-20250514", '
        '"latency_ms": %d, "diagnosis": "%s", "confidence": %.2f}',
        latency_ms,
        result.diagnosis_code,
        result.confidence_score,
    )
    return result
