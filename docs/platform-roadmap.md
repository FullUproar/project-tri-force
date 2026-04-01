# CortaLoom Platform Roadmap: The Hub & Spoke Expansion

This document outlines the definitive dependency-ordered roadmap from the current multi-specialty ASC beachhead to the final multi-spoke platform exit state. It defines the "Hub" (shared infrastructure) and the "Spokes" (vertical-specific applications), along with the strict unlock criteria required to move from one phase to the next.

## The Architectural Philosophy: Build the Hub Once

The core premise of the CortaLoom platform is that while prior authorization *data* is highly vertical-specific, the *infrastructure* required to process it is universal. 

If we build the Hub correctly during the ASC beachhead, spinning up a new Spoke should take weeks, not months. The Hub handles the heavy lifting:
- **Multi-Tenant Organization Management:** Managing BAA compliance, user roles, and data segregation.
- **Document Ingestion:** Multi-file drag-and-drop, DICOM/PDF parsing, and PHI scrubbing (Microsoft Presidio).
- **LLM Orchestration:** Routing documents to the correct prompt template based on the Organization's `vertical` flag.
- **Analytics & Audit:** Logging every extraction for HIPAA compliance and tracking "time saved" metrics.

## The Spoke Roadmap

The expansion strategy follows a strict dependency chain. We do not advance to the next Phase until the Unlock Criteria for the current phase are met. This prevents technical debt and ensures we are always building from a position of strength.

### Phase 1: The Multi-Specialty ASC Beachhead

The average Ambulatory Surgery Center (ASC) performs 2.84 specialties [1]. The most common combination is Orthopaedics, Pain Management, and Spine [1]. Therefore, the beachhead is not a single specialty, but rather the canonical multi-specialty ASC. 

The target user is the ASC Prior Auth Coordinator, who often handles both Ortho and Spine cases in the same week. The Hub infrastructure must be built to support multiple active spokes for a single customer from day one.

#### Phase 1A: Spoke 1 — Orthopaedics
Orthopaedics is the highest-acuity starting point. It is heavily reliant on complex clinical narratives (proving conservative treatments failed) [2].
*   **Primary Friction:** Synthesizing unstructured clinical notes into a persuasive justification letter.
*   **Hub Capabilities Built Here:** The entire foundational infrastructure (Auth, Database, Ingestion, PHI Scrubbing, Base LLM routing).
*   **Architectural Prerequisite:** The `vertical` flag on the `Organization` model and the Prompt Registry.

#### Phase 1B: Spoke 2 — Pain Management & Spine (Fast Follow)
Once Ortho is proven, the immediate adjacent expansion is Pain Management and Spine surgery within the *same* ASC setting. CMS and commercial payers have aggressively expanded prior authorization requirements for spinal cord stimulators, epidural steroid injections, and cervical fusions [2].
*   **Primary Friction:** Similar to Ortho (clinical justification), but with stricter imaging requirements and highly specific CMS Local Coverage Determinations (LCDs).
*   **New Capabilities Required:** A new prompt template in the registry optimized for spine LCDs and pain management conservative treatment pathways.

**Unlock Criteria to Advance to Phase 2 (Dental):**
1.  **Product:** The platform is live in production with 3 paying ASC pilots using both Ortho and Spine/Pain spokes.
2.  **Metric:** The "Time Saved" counter proves a >70% reduction in manual processing time per case across both specialties.
3.  **Data Moat:** The pgvector database has ingested >1,000 successful extractions to fine-tune the prompts.

### Phase 2: Spoke 3 — Dental (DSOs)

Dental represents the first leap outside of human medical ASCs. The Dental Support Organization (DSO) market is massive, projected to reach $58.9 billion by 2025 [3]. Dental prior authorization (predetermination) is structurally different from medical.

*   **Primary Friction:** Parsing CDT codes, analyzing X-rays for bone loss/decay, and checking strict frequency limitations (e.g., "crown covered every 5 years").
*   **Target User:** DSO Centralized Billing Office.
*   **Hub Capabilities Leveraged:** Multi-tenant organization management, API infrastructure.
*   **New Capabilities Required:** 
    *   A new `DentalExtractionResult` Pydantic schema.
    *   Integration of computer vision models (or specialized LLM vision prompts) for X-ray analysis.
    *   A new UI layout optimized for tooth charts and CDT codes.

**Unlock Criteria to Advance to Phase 3 (Veterinary):**
1.  **Product:** The Dental Spoke is piloted with one mid-sized DSO (10-50 locations).
2.  **Strategic:** Initial conversations initiated with dental software acquirers (e.g., Patterson Companies).

### Phase 3: Spoke 4 — Veterinary Medicine

Veterinary medicine is the final spoke. The U.S. pet insurance market is growing at a 15-19% CAGR, projected to reach over $18 billion by 2033 [4]. Veterinary clinics struggle with navigating multiple fragmented pet insurance portals for pre-approvals and claims [5].

*   **Primary Friction:** Invoice parsing, extracting pre-existing conditions from medical history, and formatting data for multiple disparate portals.
*   **Target User:** Veterinary Clinic Manager / Receptionist.
*   **Hub Capabilities Leveraged:** Document ingestion, LLM orchestration.
*   **New Capabilities Required:**
    *   A new `VetExtractionResult` Pydantic schema.
    *   Prompt templates optimized for veterinary species, breeds, and invoice line items.

## Summary of Architectural Prerequisites

To ensure this roadmap is viable, the following architectural decisions MUST be implemented during Phase 1A (Ortho):

1.  **The `vertical` Flag:** The `Organization` model must have a `vertical` array or enum (`ortho`, `spine`, `dental`, `vet`). This dictates all downstream logic.
2.  **The Prompt Registry:** Prompts must not be hardcoded. They must be loaded from a registry based on the organization's vertical.
3.  **Flexible Extraction Storage:** The `extraction_results` table must store data as `JSONB` and include a `schema_version` field, allowing Ortho, Dental, and Vet data to live in the same database without schema migrations.

By adhering to this roadmap and these unlock criteria, CortaLoom avoids building three separate products and instead builds a highly scalable, highly acquirable platform.

## References

[1] Surgical Information Systems. "Ambulatory Surgery Center Statistics That Define the Industry." https://blog.sisfirst.com/ambulatory-surgery-center-statistics-that-define-the-industry
[2] Becker's ASC. "5 regulatory, reimbursement changes ASCs can’t ignore." https://www.beckersasc.com/asc-coding-billing-and-collections/5-regulatory-reimbursement-changes-ascs-cant-ignore/
[3] Statifacts. "U.S. Dental Support Organizations Market Statistics 2025." https://www.statifacts.com/outlook/us-dental-support-organizations-market
[4] Yahoo Finance. "United States Pet Insurance Market Report Analysis Report 2025-2033." https://finance.yahoo.com/news/united-states-pet-insurance-market-090400540.html
[5] Wisentic. "Vets Can’t Stand Multiple Insurance Portals." https://www.wisentic.com/post/vets-dont-want-multiple-insurance-portals
