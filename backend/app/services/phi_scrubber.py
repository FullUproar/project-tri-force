import re

from app.core.logging import logger
from app.models.schemas import ScrubbedText

# --- Pass 1: Regex patterns for common PHI formats ---

_PHI_PATTERNS = [
    # SSN
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED_SSN]"),
    # MRN (various formats)
    (re.compile(r"\b(?:MRN|mrn|Medical Record Number)[:\s#]*\d{6,}\b"), "[REDACTED_MRN]"),
    # Phone numbers
    (re.compile(r"\b\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b"), "[REDACTED_PHONE]"),
    # Email addresses
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[REDACTED_EMAIL]"),
    # Dates in common formats (MM/DD/YYYY, MM-DD-YYYY, Month DD, YYYY)
    (
        re.compile(
            r"\b(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b"
        ),
        "[REDACTED_DATE]",
    ),
    (
        re.compile(
            r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
            re.IGNORECASE,
        ),
        "[REDACTED_DATE]",
    ),
    # DOB label patterns
    (
        re.compile(r"\b(?:DOB|Date of Birth|D\.O\.B\.)[:\s]*\S+", re.IGNORECASE),
        "[REDACTED_DOB]",
    ),
]


def _regex_scrub(text: str) -> tuple[str, int]:
    """Apply regex-based PHI detection. Returns (scrubbed_text, redaction_count)."""
    total_redactions = 0
    for pattern, replacement in _PHI_PATTERNS:
        text, count = pattern.subn(replacement, text)
        total_redactions += count
    return text, total_redactions


# --- Pass 2: Presidio NER-based detection ---

_analyzer = None
_anonymizer = None


def _get_presidio():
    """Lazy-load Presidio to avoid slow import at startup."""
    global _analyzer, _anonymizer
    if _analyzer is None:
        from presidio_analyzer import AnalyzerEngine
        from presidio_anonymizer import AnonymizerEngine

        _analyzer = AnalyzerEngine()
        _anonymizer = AnonymizerEngine()
    return _analyzer, _anonymizer


def _presidio_scrub(text: str) -> tuple[str, int]:
    """Apply Presidio NER-based PHI detection. Returns (scrubbed_text, redaction_count)."""
    analyzer, anonymizer = _get_presidio()

    results = analyzer.analyze(
        text=text,
        entities=[
            "PERSON",
            "PHONE_NUMBER",
            "EMAIL_ADDRESS",
            "LOCATION",
            "DATE_TIME",
            "US_SSN",
            "MEDICAL_LICENSE",
        ],
        language="en",
    )

    if not results:
        return text, 0

    anonymized = anonymizer.anonymize(text=text, analyzer_results=results)
    return anonymized.text, len(results)


# --- Public API ---


def scrub_text(text: str) -> ScrubbedText:
    """Remove PHI from text using regex + Presidio dual-pass approach.

    Returns a ScrubbedText instance that can be safely passed to LLM services.
    """
    # Pass 1: Regex (fast, deterministic)
    text, regex_count = _regex_scrub(text)

    # Pass 2: Presidio NER (catches names, locations, etc.)
    text, presidio_count = _presidio_scrub(text)

    total = regex_count + presidio_count
    if total > 0:
        logger.info("PHI scrubber removed %d entities (regex=%d, presidio=%d)",
                     total, regex_count, presidio_count)

    return ScrubbedText(text)
