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
    """Extract structured OrthoPriorAuthData from scrubbed clinical text.

    Args:
        scrubbed_text: PHI-scrubbed text (enforced by type system).

    Returns:
        OrthoPriorAuthData with extracted fields.
    """
    chain = _get_extraction_chain()
    result = await chain.ainvoke({"text": str(scrubbed_text)})

    logger.info(
        "Extraction complete: diagnosis=%s, confidence=%.2f",
        result.diagnosis_code,
        result.confidence_score,
    )
    return result
