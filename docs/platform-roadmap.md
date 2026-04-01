# CortaLoom Platform Roadmap: The Hub & Spoke Expansion

This document outlines the definitive dependency-ordered roadmap from the current Orthopaedic beachhead to the final multi-spoke platform exit state. It defines the "Hub" (shared infrastructure) and the "Spokes" (vertical-specific applications), along with the strict unlock criteria required to move from one phase to the next.

## The Architectural Philosophy: Build the Hub Once

The core premise of the CortaLoom platform is that while prior authorization *data* is highly vertical-specific, the *infrastructure* required to process it is universal. 

If we build the Hub correctly during the Ortho beachhead, spinning up a new Spoke should take weeks, not months. The Hub handles the heavy lifting:
- **Multi-Tenant Organization Management:** Managing BAA compliance, user roles, and data segregation.
- **Document Ingestion:** Multi-file drag-and-drop, DICOM/PDF parsing, and PHI scrubbing (Microsoft Presidio).
- **LLM Orchestration:** Routing documents to the correct prompt template based on the Organization's `vertical` flag.
- **Analytics & Audit:** Logging every extraction for HIPAA compliance and tracking "time saved" metrics.

## The Spoke Roadmap

The expansion strategy follows a strict dependency chain. We do not advance to the next Spoke until the Unlock Criteria for the current phase are met. This prevents technical debt and ensures we are always building from a position of strength.

### Phase 1: Spoke 1 — Orthopaedics (The Beachhead)

Orthopaedics is the perfect beachhead. It is high-acuity, high-cost, and heavily reliant on complex clinical narratives (proving conservative treatments failed) [1]. 

*   **Primary Friction:** Synthesizing unstructured clinical notes into a persuasive justification letter.
*   **Target User:** ASC Prior Auth Coordinator.
*   **Hub Capabilities Built Here:** The entire foundational infrastructure (Auth, Database, Ingestion, PHI Scrubbing, Base LLM routing).
*   **Architectural Prerequisite:** The `vertical` flag on the `Organization` model and the Prompt Registry (Issues #211, #212).

**Unlock Criteria to Advance to Phase 2:**
1.  **Product:** The Ortho Spoke is live in production with 3 paying ASC pilots.
2.  **Metric:** The "Time Saved" counter proves a >70% reduction in manual processing time per case.
3.  **Data Moat:** The pgvector database has ingested >1,000 successful orthopaedic extractions to fine-tune the prompt.

### Phase 2: Spoke 2 — Pain Management & Spine

Once Ortho is proven, the immediate adjacent expansion is Pain Management and Spine surgery within the ASC setting. As of 2026, CMS and commercial payers have aggressively expanded prior authorization requirements for spinal cord stimulators, epidural steroid injections, and cervical fusions [1]. 

*   **Primary Friction:** Similar to Ortho (clinical justification), but with stricter imaging requirements and highly specific CMS Local Coverage Determinations (LCDs).
*   **Target User:** ASC Prior Auth Coordinator (often the same person doing Ortho).
*   **Hub Capabilities Leveraged:** The existing ingestion and PHI scrubbing pipeline.
*   **New Capabilities Required:** A new prompt template in the registry optimized for spine LCDs and pain management conservative treatment pathways.

**Unlock Criteria to Advance to Phase 3:**
1.  **Product:** The Spine/Pain Spoke is live and adopted by existing Ortho ASC customers who also perform spine cases.
2.  **Metric:** Cross-sell revenue generated from existing accounts.

### Phase 3: Spoke 3 — Dental (DSOs)

Dental represents the first leap outside of human medical ASCs. The Dental Support Organization (DSO) market is massive, projected to reach $58.9 billion by 2025 [2]. Dental prior authorization (predetermination) is structurally different from medical.

*   **Primary Friction:** Parsing CDT codes, analyzing X-rays for bone loss/decay, and checking strict frequency limitations (e.g., "crown covered every 5 years").
*   **Target User:** DSO Centralized Billing Office.
*   **Hub Capabilities Leveraged:** Multi-tenant organization management, API infrastructure.
*   **New Capabilities Required:** 
    *   A new `DentalExtractionResult` Pydantic schema.
    *   Integration of computer vision models (or specialized LLM vision prompts) for X-ray analysis.
    *   A new UI layout optimized for tooth charts and CDT codes.

**Unlock Criteria to Advance to Phase 4:**
1.  **Product:** The Dental Spoke is piloted with one mid-sized DSO (10-50 locations).
2.  **Strategic:** Initial conversations initiated with dental software acquirers (e.g., Patterson Companies).

### Phase 4: Spoke 4 — Veterinary Medicine

Veterinary medicine is the final spoke. The U.S. pet insurance market is growing at a 15-19% CAGR, projected to reach over $18 billion by 2033 [3]. Veterinary clinics struggle with navigating multiple fragmented pet insurance portals for pre-approvals and claims [4].

*   **Primary Friction:** Invoice parsing, extracting pre-existing conditions from medical history, and formatting data for multiple disparate portals.
*   **Target User:** Veterinary Clinic Manager / Receptionist.
*   **Hub Capabilities Leveraged:** Document ingestion, LLM orchestration.
*   **New Capabilities Required:**
    *   A new `VetExtractionResult` Pydantic schema.
    *   Prompt templates optimized for veterinary species, breeds, and invoice line items.

## Summary of Architectural Prerequisites

To ensure this roadmap is viable, the following architectural decisions MUST be implemented during Phase 1 (Ortho):

1.  **The `vertical` Flag:** The `Organization` model must have a `vertical` enum (`ortho`, `spine`, `dental`, `vet`). This dictates all downstream logic.
2.  **The Prompt Registry:** Prompts must not be hardcoded. They must be loaded from a registry based on the organization's vertical.
3.  **Flexible Extraction Storage:** The `extraction_results` table must store data as `JSONB` and include a `schema_version` field, allowing Ortho, Dental, and Vet data to live in the same database without schema migrations.

By adhering to this roadmap and these unlock criteria, CortaLoom avoids building three separate products and instead builds a highly scalable, highly acquirable platform.

## References

[1] Becker's ASC. "5 regulatory, reimbursement changes ASCs can’t ignore." https://www.beckersasc.com/asc-coding-billing-and-collections/5-regulatory-reimbursement-changes-ascs-cant-ignore/
[2] Statifacts. "U.S. Dental Support Organizations Market Statistics 2025." https://www.statifacts.com/outlook/us-dental-support-organizations-market
[3] Yahoo Finance. "United States Pet Insurance Market Report Analysis Report 2025-2033." https://finance.yahoo.com/news/united-states-pet-insurance-market-090400540.html
[4] Wisentic. "Vets Can’t Stand Multiple Insurance Portals." https://www.wisentic.com/post/vets-dont-want-multiple-insurance-portals
