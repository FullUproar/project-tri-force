# CortaLoom Tri-Force Strategy: To Unify or Focus?

This document analyzes the viability of the "Tri-Force" platform thesis—building a unified AI prior authorization tool that spans Orthopaedics, Dental, and Veterinary medicine—versus focusing exclusively on a human medical beachhead (Orthopaedics). The analysis is grounded in the day-to-day operational realities of billing coordinators in each vertical, as well as the structural differences in how insurance claims are processed.

## 1. The Operational Reality of Prior Authorization

Across all healthcare verticals, prior authorization is universally despised by the staff who execute it. It is repetitive, opaque, and highly fragmented. However, the *nature* of the friction differs significantly between human medicine, dental, and veterinary practices.

### The Orthopaedic Reality (Human Medicine)
In orthopaedics, the primary friction point is **clinical justification** [1]. Payers (e.g., UnitedHealthcare, Medicare) require narrative proof that conservative treatments (physical therapy, NSAIDs, injections) have failed before they will approve costly surgical interventions like Total Knee Arthroplasty (TKA) [2]. The burden on the prior auth coordinator involves reading through pages of unstructured clinical notes to find specific dates and outcomes of past treatments, then synthesizing that into a compelling narrative [1]. Denials are frequent and often based on subjective interpretations of "medical necessity" [2].

### The Dental Reality
Dental insurance operates on a fundamentally different framework. While medical insurance uses CPT (Current Procedural Terminology) and ICD-10 (International Classification of Diseases) codes, dental insurance relies exclusively on CDT (Current Dental Terminology) codes [3]. The primary friction in dental billing is not narrative justification, but rather **radiographic evidence and strict policy limitations** [4]. 

Dental practices frequently deal with "predeterminations" rather than true prior authorizations [5]. A predetermination is an estimate of coverage based on remaining annual maximums, which are often very low (e.g., $1,500/year) [5]. Denials are typically technical: missing X-rays, exhausting the annual maximum, or violating frequency limitations (e.g., "insurance only covers a new crown every 5 years") [4].

### The Veterinary Reality
Veterinary insurance is property insurance, not health insurance. The patient (the pet owner) pays the vet directly out-of-pocket and then submits a claim for reimbursement [6]. True prior authorization is rare in veterinary medicine. Instead, the friction lies in **pre-approvals and claims reconciliation** [7]. 

Veterinary clinics struggle with owners who cannot afford care upfront and want the clinic to submit a pre-approval request to guarantee reimbursement before proceeding with surgery [7]. The pain point for the clinic is navigating multiple, fragmented pet insurance portals (Trupanion, Nationwide, Healthy Paws) to submit invoices and medical records [8]. According to a recent survey, 33% of veterinary staff cite navigating multiple portals as their biggest frustration [8].

## 2. The Tri-Force Thesis: Unified Platform vs. Focused Beachhead

The original Tri-Force thesis posited that Orthopaedics, Dental, and Vet could all be served by a single AI extraction and narrative generation engine. Based on the structural differences outlined above, this thesis requires refinement.

### The Case Against a Unified Extraction Engine
Building a single LLM pipeline to handle all three verticals is technologically feasible but strategically flawed. 

1.  **Different Data Primitives:** Ortho requires extracting conservative treatment histories to build narratives. Dental requires parsing CDT codes and analyzing X-rays for bone loss or decay. Vet requires invoice reconciliation and pre-existing condition checks [3] [6].
2.  **Different Output Requirements:** Ortho outputs a persuasive clinical narrative. Dental outputs a structured predetermination request with attached imaging. Vet outputs an invoice and a standardized medical record export.
3.  **Diluted "Wow" Factor:** To create a "wow" experience for the operator, the tool must feel custom-built for their specific workflow. A generic "medical/dental/vet" tool will feel clunky to all three.

### The Case for a Unified *Infrastructure* Layer
While the extraction logic must be vertical-specific, the underlying infrastructure can and should be unified. The true value of the Tri-Force platform to an acquirer (like Patterson Companies, which recently integrated AI into its dental software [9]) is the shared architecture:

*   **Multi-Tenant Organization Management:** The ability to onboard clinics, manage users, and handle BAA/compliance tracking.
*   **Document Ingestion Pipeline:** The OCR, PDF parsing, and PHI scrubbing layer (Microsoft Presidio).
*   **Integration Layer:** The API architecture designed to connect with various EHRs and Practice Management Systems (PMS).

## 3. Strategic Recommendation: The "Hub and Spoke" Execution

CortaLoom should abandon the idea of a single, generic prior auth tool. Instead, it should adopt a strict "Hub and Spoke" architecture.

**The Hub (The Unified Platform):**
This is the core infrastructure. It handles authentication (Clerk), database management (Neon Postgres), document ingestion, PHI scrubbing, and API routing. This is the asset that an acquirer buys.

**The Spokes (The Vertical Applications):**
These are the vertical-specific LLM extraction engines and frontends. 

1.  **Spoke 1: Orthopaedics (The Beachhead).** This is the current focus. The engine extracts clinical narratives for human medical payers. This is the fastest path to $1.5M ARR because the pain of denied $30,000 surgeries is acute.
2.  **Spoke 2: Dental (Fast Follow).** The engine is retooled to focus on CDT codes, frequency limitations, and predetermination workflows. The target is DSOs (Dental Support Organizations).
3.  **Spoke 3: Veterinary (Future Expansion).** The engine is retooled to focus on invoice parsing, pre-existing condition extraction, and multi-portal submission automation.

### Why This Works for the $10M Exit
Acquirers like Zimmer Biomet (Ortho) or Patterson Companies (Dental) do not want to buy a generic tool. They want to buy a tool that solves their specific industry's problem. However, if CortaLoom proves it has built a scalable *infrastructure* (The Hub) that can rapidly deploy new *applications* (The Spokes), it transitions from being a single-product company to a platform company, commanding a much higher multiple.

## 4. Next Steps for Development

To execute this strategy, the immediate development focus must remain 100% on the Orthopaedic beachhead to secure the first 3 pilot ASCs. However, the backend architecture must be refactored slightly to support the future Hub and Spoke model.

Specifically, the backend needs a `vertical` flag on the `Organization` model (e.g., `ortho`, `dental`, `vet`), which dictates which LLM extraction prompt and output schema is used for that tenant's jobs. This ensures the infrastructure is ready for expansion without polluting the current Orthopaedic focus.

## References

[1] Becker's ASC. "The payer problem ASCs say hurts patients most." https://www.beckersasc.com/asc-coding-billing-and-collections/the-payer-problem-ascs-say-hurts-patients-most/
[2] AnnexMed. "Prior Authorization Challenges in Orthopedic Practices." https://annexmed.com/prior-authorization-challenges-in-orthopedic-practices
[3] eAssist. "Medical-Dental Cross-Coding: CDT vs CPT vs ICD Explained." https://dentalbilling.com/cross-coding-medical-coverage-dental-treatments/
[4] Dental Managers. "Insurance Wars: Dealing with Insurance Companies as a Dental Practice." https://www.dentalmanagers.com/blog/dental-insurance-wars/
[5] Dental Claim Support. "When do you need predetermination vs. preauthorization? A quick guide." https://www.dentalclaimsupport.com/blog/dental-predetermination-and-preauthorizations
[6] AKC Pet Insurance. "Understanding Pet Insurance: Pre-Existing Conditions." https://www.akcpetinsurance.com/blog/preexisting-conditions-understanding-pet-insurance
[7] PawPlan. "How Pre-Authorization Works in Pet Insurance." https://pawplan.org/how-pre-authorization-works-in-pet-insurance/
[8] Wisentic. "Vets Can't Stand Multiple Insurance Portals." https://www.wisentic.com/post/vets-dont-want-multiple-insurance-portals
[9] Patterson Companies. "Patterson Dental announces Eaglesoft and Pearl Second Opinion integration." https://www.pattersoncompanies.com/news/patterson-dental-announces-eaglesoft-and-pearl-second-opinion-integration/
