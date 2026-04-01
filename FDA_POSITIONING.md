# CortaLoom FDA Regulatory Positioning

**Entity:** CortaLoom AI, Inc. (Indiana C Corporation)

## Classification: Non-Device Clinical Decision Support (CDS)

CortaLoom is **not a medical device** under the 21st Century Cures Act and FDA guidance on Clinical Decision Support software. It qualifies for the non-device CDS exemption under Section 3060 of the Cures Act.

## Four-Criteria Analysis

The FDA exempts CDS software from device regulation when it meets all four criteria:

### Criterion 1: Does not acquire, process, or analyze medical images
**Status: MEETS EXEMPTION**

CortaLoom extracts metadata from DICOM files (patient age, modality, body part, pixel spacing) for administrative purposes. It does **not** analyze the image content for diagnostic findings. No image interpretation, segmentation, or diagnostic output is performed.

### Criterion 2: Displays, analyzes, or prints medical information
**Status: MEETS EXEMPTION**

CortaLoom displays extracted clinical data (diagnosis codes, treatment history, implant selections) and generates prior authorization narratives. All information is sourced from existing provider documentation.

### Criterion 3: Supports or provides recommendations to healthcare professionals
**Status: MEETS EXEMPTION**

CortaLoom supports the administrative task of prior authorization by drafting payer submission narratives. It does **not** recommend diagnoses, treatments, or clinical decisions.

### Criterion 4: Enables independent review of the basis for recommendations
**Status: MEETS EXEMPTION**

All extracted fields display a confidence score. The source clinical text is available for comparison. Healthcare professionals can edit any extracted field before generating the narrative. The AI disclosure clearly states the tool is for review before submission.

## Key Positioning Rules

To maintain this exemption, CortaLoom must **never**:

1. ~~Diagnose patients~~ — Extract existing diagnoses from provider notes only
2. ~~Recommend treatments~~ — Extract existing treatment plans from provider notes only
3. ~~Analyze images for diagnostic purposes~~ — Extract DICOM metadata only
4. ~~Replace clinical judgment~~ — Always present data for human review and approval

## Marketing Language Guidelines

**Use:**
- "Administrative workflow automation"
- "Prior authorization extraction and generation"
- "Clinical data normalization for ASC operations"
- "AI-assisted document processing"

**Never use:**
- "Clinical decision support" (triggers FDA review)
- "Diagnostic tool" or "diagnostic AI"
- "Treatment recommendation engine"
- "Automated clinical assessment"

## References

- 21st Century Cures Act, Section 3060
- FDA Guidance: "Clinical Decision Support Software" (September 2022)
- FDA Guidance: "Policy for Device Software Functions" (September 2019)
