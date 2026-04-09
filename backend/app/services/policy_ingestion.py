"""Policy ingestion service.

Handles two ingestion paths:
1. Generating structured chunks from existing PayerPolicy rows (JSONB criteria).
2. Chunking raw text extracted from uploaded PDF policy documents.

Embeddings are intentionally left as None — retrieval is metadata-based
(payer + procedure filters). A separate embedding job can fill these later.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.database import PayerPolicy, PayerPolicyChunk, PayerPolicyDocument

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CHUNK_TARGET_SIZE = 500  # characters — target for document text chunks
_CHUNK_MIN_SIZE = 80       # don't emit chunks shorter than this

# Regex patterns used for heading detection in raw document text.
# Order matters: more specific patterns first.
_HEADING_PATTERNS: list[re.Pattern[str]] = [
    # ALL-CAPS line (3+ words or 10+ chars), possibly ending with colon
    re.compile(r"^([A-Z][A-Z\s\-/&]{9,}):?\s*$", re.MULTILINE),
    # Title Case line ending with colon
    re.compile(r"^([A-Z][A-Za-z\s\-/&]{4,}):[ \t]*$", re.MULTILINE),
    # Numbered section headings, e.g. "1. Coverage Criteria" or "II. Requirements"
    re.compile(r"^([IVXLCDM]+\.|[0-9]+\.)\s+([A-Z][A-Za-z\s\-/&]{3,})$", re.MULTILINE),
]


# ---------------------------------------------------------------------------
# Internal: policy-to-chunk conversion
# ---------------------------------------------------------------------------


def _fmt_months(value: Any) -> str:
    """Return a human-readable duration string from a month count."""
    if value is None:
        return "unspecified duration"
    try:
        months = int(value)
    except (TypeError, ValueError):
        return str(value)
    if months == 1:
        return "1 month"
    if months % 12 == 0:
        years = months // 12
        return f"{years} year{'s' if years != 1 else ''}"
    return f"{months} months"


def _fmt_list(items: Any, fallback: str = "none specified") -> str:
    """Return a comma-joined string from a list, or fallback."""
    if not items:
        return fallback
    if isinstance(items, list):
        return ", ".join(str(i) for i in items)
    return str(items)


def _generate_policy_chunks(policy: PayerPolicy) -> list[dict[str, Any]]:
    """Convert a PayerPolicy record into a list of chunk dicts.

    Each dict contains the fields needed to construct a PayerPolicyChunk row:
    payer, procedure, section_title, content, chunk_index.
    The caller is responsible for setting policy_id, id, etc.
    """
    c: dict[str, Any] = policy.criteria or {}
    payer = policy.payer
    procedure = policy.procedure

    chunks: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # 1. Overview chunk
    # ------------------------------------------------------------------
    conservative_min = _fmt_months(c.get("conservative_treatment_min_months"))
    modalities = _fmt_list(c.get("required_modalities"), "standard conservative measures")
    imaging_req = "imaging is required" if c.get("imaging_required") else "imaging is not explicitly required"
    functional_req = (
        "functional impairment documentation is required"
        if c.get("functional_impairment_required")
        else "functional impairment documentation is not explicitly required"
    )
    overview_content = (
        f"{payer} requires prior authorization for {procedure}. "
        f"Conservative treatment of at least {conservative_min} must be documented. "
        f"Required treatment modalities include {modalities}. "
        f"Additionally, {imaging_req} and {functional_req}."
    )
    chunks.append(
        {
            "section_title": f"Policy Overview — {payer} {procedure}",
            "content": overview_content,
            "chunk_index": 0,
        }
    )

    # ------------------------------------------------------------------
    # 2. Conservative Treatment chunk
    # ------------------------------------------------------------------
    modalities_detail = _fmt_list(c.get("required_modalities"), "no specific modalities listed")
    conservative_content = (
        f"{payer} {procedure} conservative treatment requirements: "
        f"the member must complete a minimum of {conservative_min} of conservative therapy "
        f"prior to surgical authorization. "
        f"Required treatment modalities are: {modalities_detail}. "
        f"Documentation of each completed modality and the member's response must be included in the submission."
    )
    chunks.append(
        {
            "section_title": "Conservative Treatment Requirements",
            "content": conservative_content,
            "chunk_index": 1,
        }
    )

    # ------------------------------------------------------------------
    # 3. Imaging Requirements chunk
    # ------------------------------------------------------------------
    imaging_required: bool = bool(c.get("imaging_required"))
    imaging_max_age = c.get("imaging_max_age_months")
    if imaging_required:
        if imaging_max_age is not None:
            recency_clause = (
                f"Images must be no older than {_fmt_months(imaging_max_age)} at the time of submission."
            )
        else:
            recency_clause = "No explicit recency requirement is specified, but current imaging is recommended."
        imaging_content = (
            f"{payer} requires imaging for {procedure} authorization. "
            f"{recency_clause} "
            f"Acceptable modalities typically include X-ray, MRI, or CT as clinically appropriate. "
            f"Imaging must be interpreted by a qualified radiologist and the report included in the prior authorization packet."
        )
    else:
        imaging_content = (
            f"{payer} does not explicitly require imaging for {procedure} authorization. "
            f"However, supporting imaging may strengthen the clinical justification. "
            f"If imaging has been obtained, include the radiology report in the submission."
        )
    chunks.append(
        {
            "section_title": "Imaging Requirements",
            "content": imaging_content,
            "chunk_index": 2,
        }
    )

    # ------------------------------------------------------------------
    # 4. Functional Requirements chunk
    # ------------------------------------------------------------------
    functional_required: bool = bool(c.get("functional_impairment_required"))
    if functional_required:
        functional_content = (
            f"{payer} requires documented functional impairment for {procedure} authorization. "
            f"The clinical record must include objective measures of functional limitation such as "
            f"range-of-motion measurements, validated functional outcome scores (e.g., KOOS, ODI, VAS), "
            f"or physician assessment of activities-of-daily-living impairment. "
            f"Subjective pain complaints alone are insufficient; objective functional decline must be demonstrated."
        )
    else:
        functional_content = (
            f"{payer} does not list functional impairment documentation as a hard requirement for "
            f"{procedure} authorization. "
            f"Including objective functional outcome measures is still strongly recommended as supporting evidence "
            f"and may reduce the likelihood of a peer-to-peer review request."
        )
    chunks.append(
        {
            "section_title": "Functional Impairment Documentation",
            "content": functional_content,
            "chunk_index": 3,
        }
    )

    # ------------------------------------------------------------------
    # 5. Special Requirements chunk (trial, BMI, other)
    # ------------------------------------------------------------------
    trial_required: bool = bool(c.get("trial_required"))
    bmi_threshold = c.get("bmi_threshold")
    extra_parts: list[str] = []

    if trial_required:
        extra_parts.append(
            f"{payer} requires documentation of a failed trial period before approving {procedure}."
        )
    if bmi_threshold is not None:
        try:
            bmi_val = float(bmi_threshold)
            extra_parts.append(
                f"A BMI threshold applies: the member's BMI must meet or exceed {bmi_val:.1f} "
                f"as documented in the medical record."
            )
        except (TypeError, ValueError):
            extra_parts.append(f"A BMI requirement applies: {bmi_threshold}.")

    # Collect any remaining unknown criteria keys as a catch-all
    known_keys = {
        "conservative_treatment_min_months",
        "required_modalities",
        "imaging_required",
        "imaging_max_age_months",
        "functional_impairment_required",
        "trial_required",
        "bmi_threshold",
        "submission_portal",
    }
    for key, val in c.items():
        if key not in known_keys and val not in (None, "", [], {}):
            readable_key = key.replace("_", " ").capitalize()
            extra_parts.append(f"{readable_key}: {val}.")

    if extra_parts:
        special_content = (
            f"Additional requirements for {payer} {procedure} authorization: "
            + " ".join(extra_parts)
        )
    else:
        special_content = (
            f"No additional special requirements (trial mandates, BMI thresholds, or other criteria) "
            f"are documented for {payer} {procedure} at this time. "
            f"Verify directly with {payer} for any recent policy amendments."
        )
    chunks.append(
        {
            "section_title": "Special Requirements",
            "content": special_content,
            "chunk_index": 4,
        }
    )

    # ------------------------------------------------------------------
    # 6. Submission Info chunk
    # ------------------------------------------------------------------
    portal = c.get("submission_portal")
    source_url = policy.source_url
    if portal:
        portal_clause = f"Submit the prior authorization request through the {payer} provider portal: {portal}."
    else:
        portal_clause = (
            f"No specific submission portal is recorded for {payer} {procedure}. "
            f"Contact {payer} provider relations or use the standard fax/portal on file."
        )
    if source_url:
        source_clause = f"The full policy document is available at: {source_url}."
    else:
        source_clause = "No source URL is currently recorded for this policy."
    submission_content = (
        f"Submission information for {payer} {procedure} prior authorization. "
        f"{portal_clause} "
        f"{source_clause} "
        f"Ensure all supporting documentation is attached before submission to avoid delays."
    )
    chunks.append(
        {
            "section_title": "Submission Information",
            "content": submission_content,
            "chunk_index": 5,
        }
    )

    # Attach payer/procedure to every chunk dict
    for chunk in chunks:
        chunk["payer"] = payer
        chunk["procedure"] = procedure

    return chunks


# ---------------------------------------------------------------------------
# Internal: heading-aware text splitter
# ---------------------------------------------------------------------------


def _detect_headings(text: str) -> list[tuple[int, str]]:
    """Return a sorted list of (char_offset, heading_text) tuples found in text."""
    found: list[tuple[int, str]] = []
    seen_spans: set[int] = set()

    for pattern in _HEADING_PATTERNS:
        for match in pattern.finditer(text):
            start = match.start()
            if start in seen_spans:
                continue
            seen_spans.add(start)
            # Use the last named/unnamed group that captured text
            heading_text = (match.group(len(match.groups())) or match.group(0)).strip().rstrip(":")
            found.append((start, heading_text))

    found.sort(key=lambda x: x[0])
    return found


def _split_text_into_chunks(
    text: str,
    target_size: int = _CHUNK_TARGET_SIZE,
    min_size: int = _CHUNK_MIN_SIZE,
) -> list[dict[str, Any]]:
    """Split raw text into heading-aware chunks.

    Returns a list of dicts with keys:
        section_title, content, chunk_index, char_start, char_end, page_number
    Page numbers are approximated by tracking form-feed characters (\\f) or
    the marker "--- Page N ---" sometimes inserted by PDF extractors.
    """
    if not text:
        return []

    headings = _detect_headings(text)
    # Build a page-break map: list of char offsets where a new page starts
    page_breaks: list[int] = [0]
    for match in re.finditer(r"\f|---\s*[Pp]age\s+\d+\s*---", text):
        page_breaks.append(match.start())

    def _page_at(offset: int) -> int:
        """1-based page number for a given char offset."""
        page = 1
        for pb in page_breaks:
            if pb <= offset:
                page += 1
            else:
                break
        return max(1, page - 1)

    # Determine section boundaries: each heading starts a new section.
    # We also force a boundary every `target_size * 2` chars even without a heading.
    boundaries: list[tuple[int, str]] = []
    last_forced = 0
    heading_offsets = {h[0] for h in headings}

    # Walk through the text collecting split points
    i = 0
    current_section = "Policy Document"
    heading_idx = 0

    # Build ordered list of all split points with their titles
    all_boundaries: list[tuple[int, str]] = [(0, current_section)]
    for h_offset, h_title in headings:
        all_boundaries.append((h_offset, h_title))

    # Add forced hard breaks between headings where gaps are very large
    extra_breaks: list[tuple[int, str]] = []
    for idx in range(len(all_boundaries)):
        start = all_boundaries[idx][0]
        end = all_boundaries[idx + 1][0] if idx + 1 < len(all_boundaries) else len(text)
        section_title = all_boundaries[idx][1]
        pos = start
        part = 1
        while (end - pos) > target_size * 2:
            pos += target_size
            extra_breaks.append((pos, f"{section_title} (continued)"))

    all_boundaries = sorted(all_boundaries + extra_breaks, key=lambda x: x[0])

    # Now produce final chunks from the boundary list
    results: list[dict[str, Any]] = []
    chunk_index = 0

    for idx, (b_start, b_title) in enumerate(all_boundaries):
        b_end = all_boundaries[idx + 1][0] if idx + 1 < len(all_boundaries) else len(text)
        segment = text[b_start:b_end].strip()

        if not segment:
            continue

        # Sub-split segment into target_size pieces
        pos = 0
        while pos < len(segment):
            raw_chunk = segment[pos: pos + target_size]

            # Try to break at a sentence boundary to avoid mid-sentence cuts
            if pos + target_size < len(segment):
                # Look for last sentence-end within the last 100 chars of the raw chunk
                sentence_end = max(
                    raw_chunk.rfind(". "),
                    raw_chunk.rfind(".\n"),
                    raw_chunk.rfind("? "),
                    raw_chunk.rfind("! "),
                )
                if sentence_end > target_size // 2:
                    raw_chunk = raw_chunk[: sentence_end + 1]

            content = raw_chunk.strip()
            if len(content) < min_size:
                pos += len(raw_chunk)
                continue

            char_start = b_start + pos
            char_end = char_start + len(raw_chunk)

            results.append(
                {
                    "section_title": b_title,
                    "content": content,
                    "chunk_index": chunk_index,
                    "char_start": char_start,
                    "char_end": char_end,
                    "page_number": _page_at(char_start),
                }
            )
            chunk_index += 1
            pos += len(raw_chunk)

    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def seed_chunks_from_policies(db: AsyncSession) -> int:
    """Generate and persist PayerPolicyChunk rows for all active PayerPolicy records.

    Clears any existing policy-sourced chunks (policy_id IS NOT NULL) before
    re-seeding, so this function is idempotent and safe to call on re-runs.

    Args:
        db: An active async SQLAlchemy session.

    Returns:
        The number of chunks inserted.
    """
    logger.info("seed_chunks_from_policies: clearing existing policy-sourced chunks")
    await db.execute(
        delete(PayerPolicyChunk).where(PayerPolicyChunk.policy_id.isnot(None))
    )
    await db.flush()

    result = await db.execute(
        select(PayerPolicy).where(PayerPolicy.status == "active")
    )
    policies = result.scalars().all()
    logger.info("seed_chunks_from_policies: found %d active policies", len(policies))

    total_inserted = 0
    for policy in policies:
        chunk_dicts = _generate_policy_chunks(policy)
        for cd in chunk_dicts:
            chunk = PayerPolicyChunk(
                id=uuid.uuid4(),
                policy_id=policy.id,
                document_id=None,
                payer=cd["payer"],
                procedure=cd["procedure"],
                section_title=cd["section_title"],
                content=cd["content"],
                chunk_index=cd["chunk_index"],
                embedding=None,
                page_number=None,
                char_start=None,
                char_end=None,
            )
            db.add(chunk)
            total_inserted += 1

        logger.info(
            "seed_chunks_from_policies: generated %d chunks for policy %s (%s / %s)",
            len(chunk_dicts),
            policy.id,
            policy.payer,
            policy.procedure,
        )

    await db.commit()
    logger.info("seed_chunks_from_policies: committed %d total chunks", total_inserted)
    return total_inserted


async def chunk_document(
    db: AsyncSession,
    doc: PayerPolicyDocument,
    text: str,
) -> int:
    """Chunk a raw text document and persist the chunks.

    Existing chunks for this document are deleted first so the function is
    safe to call multiple times (e.g. on document re-processing).

    Args:
        db:   An active async SQLAlchemy session.
        doc:  The PayerPolicyDocument row the chunks belong to.
        text: Raw text extracted from the document (e.g. via PDF extraction).

    Returns:
        The number of chunks inserted.
    """
    logger.info(
        "chunk_document: chunking document %s (%s / %s), text length=%d",
        doc.id,
        doc.payer,
        doc.procedure,
        len(text),
    )

    # Clear stale chunks for this document
    await db.execute(
        delete(PayerPolicyChunk).where(PayerPolicyChunk.document_id == doc.id)
    )
    await db.flush()

    chunk_dicts = _split_text_into_chunks(text)
    for cd in chunk_dicts:
        chunk = PayerPolicyChunk(
            id=uuid.uuid4(),
            document_id=doc.id,
            policy_id=None,
            payer=doc.payer,
            procedure=doc.procedure,
            section_title=cd.get("section_title"),
            content=cd["content"],
            chunk_index=cd["chunk_index"],
            embedding=None,
            page_number=cd.get("page_number"),
            char_start=cd.get("char_start"),
            char_end=cd.get("char_end"),
        )
        db.add(chunk)

    # Update the document's total_chunks counter
    doc.total_chunks = len(chunk_dicts)

    await db.commit()
    logger.info(
        "chunk_document: inserted %d chunks for document %s",
        len(chunk_dicts),
        doc.id,
    )
    return len(chunk_dicts)
