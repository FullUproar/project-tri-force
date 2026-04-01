from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

from app.config import settings
from app.core.logging import logger
from app.models.schemas import OrthoPriorAuthData
from app.services.llm.prompts import NARRATIVE_SYSTEM_PROMPT

PROMPT_VERSION = "v1.0"
MODEL_NAME = "claude-sonnet-4-20250514"


def _get_narrative_chain():
    llm = ChatAnthropic(
        model=MODEL_NAME,
        temperature=0.3,
        api_key=settings.anthropic_api_key.get_secret_value(),
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", NARRATIVE_SYSTEM_PROMPT),
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
) -> tuple[str, str, str]:
    """Generate a payer submission narrative from extraction results.

    Args:
        extraction: The structured extraction data.
        additional_context: Optional DICOM metadata or other context.

    Returns:
        Tuple of (narrative_text, model_used, prompt_version).
    """
    chain = _get_narrative_chain()

    result = await chain.ainvoke({
        "diagnosis_code": extraction.diagnosis_code,
        "treatments": ", ".join(extraction.conservative_treatments_failed),
        "implant": extraction.implant_type_requested,
        "robotic": "Yes" if extraction.robotic_assistance_required else "No",
        "justification": extraction.clinical_justification,
        "additional_context": additional_context or "None provided",
    })

    narrative_text = result.content
    logger.info("Generated narrative: %d characters", len(narrative_text))

    return narrative_text, MODEL_NAME, PROMPT_VERSION
