# CortaLoom Payer Policy Intelligence Brief: Ortho & Spine

This document outlines the prior authorization requirements for orthopedic and spine surgeries across the top 5 U.S. commercial payers. It serves as the foundational data model for the Payer Policy Scraper (Issue #201) and the Payer-Specific Templates (Issue #205).

## The Data Model for the Scraper (Issue #201)

The scraper must extract and structure the following data points for each payer policy it processes:

1.  **Payer Name:** (e.g., UnitedHealthcare, Aetna, Cigna)
2.  **Procedure Category:** (e.g., Spine, Arthroplasty, Arthroscopy)
3.  **Covered CPT Codes:** A list of all CPT codes requiring prior authorization under this policy.
4.  **Clinical Criteria (The "Must Haves"):**
    *   **Conservative Treatment Duration:** (e.g., 6 weeks, 3 months)
    *   **Required Conservative Modalities:** (e.g., PT, NSAIDs, epidural injections)
    *   **Required Imaging:** (e.g., MRI within last 6 months, X-ray showing joint space narrowing)
    *   **Functional Impairment:** (e.g., Documented impact on Activities of Daily Living - ADLs)
5.  **Submission Method:** (e.g., Portal URL, Fax number)
6.  **Common Denial Reasons:** Known pitfalls for this specific policy.

## Top 5 Payer Profiles: Ortho & Spine

### 1. UnitedHealthcare (UHC)

UHC has extensive and specific requirements for orthopedic and spine procedures.

*   **CPT Codes Requiring PA:** Extensive list covering Arthroplasty (e.g., 27130, 27447), Arthroscopy (e.g., 29881, 29827), and Spinal Surgery (e.g., 22551, 63030) [1].
*   **Clinical Documentation Required:**
    *   Detailed description of the medical condition and patient history.
    *   Specific details on symptoms, pain location, severity, and functional impairment affecting ADLs.
    *   **Conservative Treatment:** History and duration of previous therapy (PT, medications, injections) that failed or were contraindicated [1].
    *   **Imaging:** Complete reports of diagnostic tests (MRI, CT, X-ray). Images must be submitted via the external portal, not fax [1].
*   **Submission Method:** UHC Provider Portal (`UHCprovider.com`) via the Prior Authorization and Notification tool [1].
*   **Common Denial Reasons:** Missing prior authorization, insufficient clinical evidence (especially regarding conservative treatment failure), and procedures deemed experimental or investigational [1].

### 2. Aetna

Aetna's policies are detailed in their Clinical Policy Bulletins (CPBs).

*   **CPT Codes Requiring PA:** Covers major joint replacements, spinal surgeries (fusions, laminectomies), and arthroscopic procedures [1].
*   **Clinical Documentation Required:**
    *   **Conservative Treatment:** Strict requirements for documented failure of conservative management, typically spanning **3 to 6 months** depending on the procedure. This includes physical therapy, NSAIDs, and weight loss (for joint replacements) [1].
    *   **Imaging:** Recent imaging (usually within 6 months) confirming the diagnosis (e.g., severe osteoarthritis on X-ray, disc herniation on MRI) [1].
    *   **Functional Assessment:** Clear documentation of how the condition limits daily activities [1].
*   **Submission Method:** Availity provider portal or Aetna's direct electronic submission tools [1].
*   **Common Denial Reasons:** Failure to meet the strict duration requirements for conservative treatment, or lack of recent, confirmatory imaging [1].

### 3. Blue Cross Blue Shield (BCBS)

Requirements vary significantly by state/regional plan, but general patterns exist.

*   **CPT Codes Requiring PA:** Standard orthopedic and spine codes (joint replacements, spinal fusions, complex arthroscopies) [1].
*   **Clinical Documentation Required:**
    *   **Conservative Treatment:** Generally requires **6 weeks to 3 months** of documented conservative therapy (PT, home exercise program, medications) [1].
    *   **Imaging:** Corroborating imaging reports (X-ray, MRI, CT) are mandatory [1].
    *   **Functional Status:** Documentation of significant pain and functional limitation [1].
*   **Submission Method:** Varies by local BCBS plan; typically via their specific provider portal (e.g., Availity, or a proprietary state portal) [1].
*   **Common Denial Reasons:** Insufficient documentation of conservative therapy, or lack of objective imaging findings matching the clinical presentation [1].

### 4. Cigna

Cigna utilizes eviCore healthcare for managing many musculoskeletal prior authorizations.

*   **CPT Codes Requiring PA:** Spine surgery, large joint replacements (hip, knee, shoulder), and advanced imaging [1].
*   **Clinical Documentation Required:**
    *   **Conservative Treatment:** Requires documented failure of conservative care, often specifying the types of therapy (e.g., supervised PT, injections) and duration (e.g., **6 weeks**) [1].
    *   **Imaging:** Recent advanced imaging (MRI/CT) is frequently required for spine procedures [1].
    *   **Clinical Notes:** Recent clinic notes detailing the history of present illness and physical exam findings [1].
*   **Submission Method:** Primarily through the eviCore healthcare web portal [1].
*   **Common Denial Reasons:** Lack of objective evidence of pathology on imaging, or failure to complete the required duration of conservative care [1].

### 5. Humana

Humana also often partners with third-party benefits managers (like Cohere Health or HealthHelp) for musculoskeletal services.

*   **CPT Codes Requiring PA:** Spinal fusions, joint replacements, and certain arthroscopic procedures [1].
*   **Clinical Documentation Required:**
    *   **Conservative Treatment:** Documented trial and failure of conservative measures (PT, NSAIDs, bracing) [1].
    *   **Imaging:** X-ray or MRI reports confirming the diagnosis [1].
    *   **Functional Impairment:** Evidence that the condition significantly interferes with daily life [1].
*   **Submission Method:** Via the Humana provider portal or the specific portal of their delegated benefits manager (e.g., Cohere Health) [1].
*   **Common Denial Reasons:** Incomplete clinical notes, missing imaging reports, or failure to demonstrate medical necessity based on their specific criteria [1].

## Strategic Implications for CortaLoom

1.  **The "Conservative Treatment" Bottleneck:** Across all 5 payers, the most common denial reason is insufficient documentation of conservative treatment. The CortaLoom LLM must be hyper-focused on extracting:
    *   Start and end dates of Physical Therapy.
    *   Specific medications prescribed (NSAIDs, steroids) and duration of use.
    *   Dates and outcomes of previous injections (epidural, cortisone).
2.  **Imaging Recency:** The LLM must flag the date of the most recent MRI/X-ray. If it is older than 6 months, the Payer Readiness Score (Issue #218) should trigger a warning.
3.  **Portal Fragmentation:** Submission methods vary wildly (UHCprovider, Availity, eviCore, Cohere). CortaLoom's long-term value is not just generating the letter, but eventually automating the portal submission itself (RPA/Browser automation).

## References

[1] User Persona Research. "Payer Requirements for Orthopedic and Spine Surgery." /home/ubuntu/parallel_research.json
