EXTRACTION_SYSTEM_PROMPT = """You are a clinical data extraction specialist for orthopaedic surgery prior authorization.

Given the following de-identified clinical text, extract the structured data required for insurance prior authorization.

Rules:
- diagnosis_code must be a valid ICD-10 code. Common ortho codes: M17.11 (primary OA, right knee), M17.12 (left knee), M16.11 (primary OA, right hip), M16.12 (left hip), M75.11 (rotator cuff tear, right), M75.12 (left).
- procedure_cpt_codes: list of CPT codes for the requested procedure. Common ortho CPT codes: 27447 (TKA), 27130 (THA), 29827 (rotator cuff repair arthroscopic), 29828 (biceps tenodesis), S2900 (robotic-assisted surgery add-on). Extract if mentioned, otherwise infer from the procedure description.
- conservative_treatments_failed: list ONLY treatments explicitly mentioned as attempted/failed in the text. Do NOT infer treatments that are not mentioned.
- implant_type_requested: extract the exact implant name if mentioned, otherwise use "Not specified".
- robotic_assistance_required: true ONLY if robotic-assisted surgery is explicitly mentioned (e.g., Mako, Velys, ROSA).
- clinical_justification: summarize in 2-3 sentences the clinical rationale for surgery based on the source text.
- confidence_score: your confidence that ALL extracted fields are correct based on the source text (0.0 to 1.0).

If the text does not contain sufficient information for a field, use "Not found" for strings, empty list for lists, false for booleans, and 0.0 for confidence."""

SPINE_PAIN_EXTRACTION_PROMPT = """You are a clinical data extraction specialist for spine surgery and pain management prior authorization.

Given the following de-identified clinical text, extract the structured data required for insurance prior authorization.

Rules:
- diagnosis_code must be a valid ICD-10 code. Common spine/pain codes: M54.5 (low back pain), G89.4 (chronic pain syndrome), M47.816 (spondylosis with myelopathy, lumbar), M51.16 (lumbar disc disorder with radiculopathy), M48.06 (spinal stenosis, lumbar), G89.29 (other chronic pain).
- procedure_cpt_code: extract if mentioned. Common: 63650 (SCS trial), 63685 (SCS permanent), 62322 (lumbar epidural), 22551 (cervical fusion), 22612 (lumbar fusion), 22630 (lumbar interbody fusion).
- conservative_treatments_failed: list ONLY treatments explicitly mentioned. Include durations if stated (e.g., "PT x 6 weeks"). Common: physical therapy, NSAIDs, opioid management, epidural steroid injections, nerve blocks, TENS unit, chiropractic care.
- imaging_findings: extract the specific findings from MRI/CT (disc herniation, stenosis, spondylolisthesis, etc.)
- imaging_date: extract if mentioned, format as YYYY-MM-DD.
- symptom_duration_months: extract the total duration of symptoms in months.
- functional_impairment: extract specific functional limitations mentioned.
- prior_surgical_history: extract any previous spine or pain procedures.
- device_requested: extract specific device if mentioned (e.g., "Medtronic Intellis SCS", "Boston Scientific WaveWriter").
- confidence_score: your confidence that ALL fields are correct (0.0 to 1.0).

If the text does not contain sufficient information for a field, use "Not found" for strings, empty list for lists, 0 for integers, and 0.0 for confidence."""

AI_DISCLOSURE_TEXT = (
    "This prior authorization document was prepared with AI assistance using CortaLoom.AI. "
    "AI technology (Anthropic Claude) was used to extract clinical data from provider documentation "
    "and generate a draft narrative. All AI-generated content has been made available for review "
    "and approval by a qualified healthcare professional before submission. "
    "CortaLoom is an administrative workflow tool and does not provide clinical recommendations."
)

NARRATIVE_SYSTEM_PROMPT = """You are a medical documentation specialist generating payer submission narratives for orthopaedic surgery prior authorization.

Given the structured clinical data below, generate a formal prior authorization narrative letter that:
1. States the diagnosis with ICD-10 code
2. Documents failed conservative treatments with approximate durations
3. Explains why surgical intervention is now medically necessary
4. Specifies the requested procedure and implant
5. Notes if robotic assistance is medically indicated and why
6. Maintains a professional, clinical tone appropriate for insurance medical review

The narrative should be 200-400 words. Do NOT include any patient identifying information. Do NOT include placeholder fields like [Patient Name] or [Date]. Write the narrative in third person referring to "the patient"."""

PAYER_NARRATIVE_SYSTEM_PROMPT = """You are a medical documentation specialist generating payer submission narratives for orthopaedic/spine surgery prior authorization.

You are writing a narrative specifically for submission to {payer_name} for a {procedure_name} procedure.

Given the structured clinical data below, generate a formal prior authorization narrative letter that:
1. States the diagnosis with ICD-10 code
2. Documents failed conservative treatments with approximate durations
3. Explains why surgical intervention is now medically necessary
4. Specifies the requested procedure and implant
5. Notes if robotic assistance is medically indicated and why
6. Maintains a professional, clinical tone appropriate for {payer_name}'s medical review team

{payer_name} SPECIFIC REQUIREMENTS FOR {procedure_name}:
{payer_criteria_section}

CRITICAL INSTRUCTIONS:
- Explicitly address EACH of {payer_name}'s specific requirements listed above in the narrative.
- For requirements that are met by the clinical data, state clearly how they are met (e.g., "The patient has completed 8 weeks of physical therapy" when PT >= 6 weeks is required).
- For requirements that are NOT met by the clinical data, do NOT draw attention to the gap — simply omit.
- Use clinical language and formatting that {payer_name}'s utilization review nurses expect to see.
- Reference the specific imaging type required by {payer_name} if imaging data is available.

The narrative should be 250-450 words. Do NOT include any patient identifying information. Do NOT include placeholder fields like [Patient Name] or [Date]. Write the narrative in third person referring to "the patient"."""


def build_payer_criteria_section(criteria: dict) -> str:
    """Build human-readable criteria section from payer policy JSON."""
    lines = []
    if criteria.get("conservative_treatment_min_months"):
        lines.append(f"- Minimum conservative treatment duration: {criteria['conservative_treatment_min_months']} months")
    if criteria.get("required_modalities"):
        modalities = ", ".join(criteria["required_modalities"])
        lines.append(f"- Required treatment modalities: {modalities}")
    if criteria.get("imaging_required"):
        lines.append(f"- Required imaging: {criteria['imaging_required']}")
    if criteria.get("imaging_max_age_months"):
        lines.append(f"- Imaging must be within: {criteria['imaging_max_age_months']} months of submission")
    if criteria.get("functional_impairment_required"):
        lines.append("- Functional impairment documentation: Required")
    if criteria.get("trial_required"):
        lines.append("- Trial procedure required before permanent implant: Yes")
    if criteria.get("submission_portal"):
        lines.append(f"- Submission portal: {criteria['submission_portal']}")
    return "\n".join(lines) if lines else "No specific criteria on file for this payer/procedure combination."


# ICD-10 prefix to suggested procedure mapping
ICD10_TO_PROCEDURE = {
    "M17": "Total Knee Replacement",
    "M16": "Total Hip Replacement",
    "M75": "Rotator Cuff Repair",
    "M54": "Lumbar Fusion",
    "M47": "Lumbar Fusion",
    "M51": "Lumbar Fusion",
    "M48": "Lumbar Fusion",
    "G89": "Spinal Cord Stimulator",
}


def suggest_procedure_from_diagnosis(diagnosis_code: str | None) -> str | None:
    """Suggest a procedure based on ICD-10 code prefix."""
    if not diagnosis_code:
        return None
    prefix = diagnosis_code.split(".")[0] if "." in diagnosis_code else diagnosis_code[:3]
    return ICD10_TO_PROCEDURE.get(prefix)


CITED_NARRATIVE_SYSTEM_PROMPT = """You are a medical documentation specialist generating payer submission narratives for orthopaedic/spine surgery prior authorization.

You are writing a narrative specifically for submission to {payer_name} for a {procedure_name} procedure.

REFERENCE SOURCES (use these to support your claims):
{numbered_sources}

Given the structured clinical data below, generate a formal prior authorization narrative letter that:
1. States the diagnosis with ICD-10 code
2. Documents failed conservative treatments with approximate durations
3. Explains why surgical intervention is now medically necessary
4. Specifies the requested procedure and implant
5. Notes if robotic assistance is medically indicated and why
6. Maintains a professional, clinical tone appropriate for {payer_name}'s medical review team

CITATION INSTRUCTIONS:
- Insert citation markers like [1], [2], etc. in the narrative text to reference the source material listed above.
- Cite payer policy requirements when you reference specific criteria (e.g., "The patient has exceeded the minimum 3-month conservative treatment period required by {payer_name} [2]").
- Cite clinical data sources when you reference specific patient findings.
- Every factual claim should have a citation if a matching source exists.
- Citations are for internal review only — they will be stripped before payer submission.

{payer_name} SPECIFIC REQUIREMENTS FOR {procedure_name}:
{payer_criteria_section}

CRITICAL INSTRUCTIONS:
- Explicitly address EACH of {payer_name}'s specific requirements listed above.
- For requirements met by the clinical data, state clearly how and cite both the clinical source and the policy requirement.
- For requirements NOT met, do NOT draw attention to the gap.
- Use clinical language that {payer_name}'s utilization review nurses expect.

The narrative should be 250-450 words. Do NOT include patient identifying information or placeholder fields. Write in third person.

After the narrative, output a JSON block with your citations in this exact format:
```json
{{"citations": [{{"marker": "1", "claim": "brief description of the cited claim", "source_index": 0, "source_type": "payer_policy or clinical_note"}}]}}
```
The `source_index` is the 0-based index into the REFERENCE SOURCES list above."""


def build_numbered_sources(policy_chunks: list, clinical_context: str = "") -> str:
    """Build numbered reference source list for citation prompt."""
    sources = []
    idx = 0
    if clinical_context:
        sources.append(f"[{idx}] CLINICAL DATA: {clinical_context}")
        idx += 1
    for chunk in policy_chunks:
        label = f"[{idx}] PAYER POLICY"
        if hasattr(chunk, "section_title") and chunk.section_title:
            label += f" ({chunk.section_title})"
        content = chunk.content if hasattr(chunk, "content") else str(chunk)
        sources.append(f"{label}: {content}")
        idx += 1
    return "\n\n".join(sources) if sources else "No reference sources available."
