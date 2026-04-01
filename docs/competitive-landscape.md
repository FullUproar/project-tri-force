# Competitive Landscape: AI-Powered Prior Authorization

This document analyzes the current competitive landscape for AI-powered prior authorization automation as of April 2026. It maps the major incumbents, emerging AI startups, and identifies the specific "white space" that CortaLoom AI is positioned to capture.

## 1. The Incumbents (The Clearinghouses)

The market is currently dominated by massive clearinghouses that have bolted on "AI" features to their legacy EDI infrastructure.

### Waystar
*   **What they do:** Revenue cycle management (RCM) platform. Their "Authorization Manager" auto-populates payer portals and checks statuses via screen scraping and EDI connections [1, 2].
*   **Customers:** Massive footprint. Health systems, hospitals, and explicitly ASCs [1, 4].
*   **Pricing:** Custom enterprise pricing, often bundled with other RCM modules. High implementation fees ($2k-$10k+) [6].
*   **Valuation:** Public company (IPO June 2024), current market cap ~$5B [8, 10].
*   **The Gap:** Waystar focuses on the *submission* and *status checking* mechanics. They do not deeply understand the clinical narrative. They rely on the provider to have already determined that the clinical criteria are met. They are an administrative router, not a clinical reasoning engine.

### Availity
*   **What they do:** Multi-payer provider portal ("Availity Essentials"). They are the pipes connecting providers to payers. They recently launched "AuthAI" for real-time recommendations and partnered with Abridge [15, 17].
*   **Customers:** 3 million providers, heavily entrenched with payers [15, 18].
*   **Pricing:** Basic portal is free (sponsored by payers). Premium tiers exist [20].
*   **Valuation:** Estimated ~$5B (backed by Novo Holdings) [23, 24].
*   **The Gap:** Availity is fundamentally a payer-centric tool. Their goal is to make it easier for providers to submit data *in the format the payer wants*. Their UI is notoriously clunky, and they do not specialize in extracting the "why" from unstructured clinical notes for complex surgical cases.

## 2. The AI-Native Entrants (The Clinical Intelligence Layer)

These companies emerged specifically to apply LLMs to the prior auth problem, but they have largely targeted massive health systems and payers.

### Cohere Health
*   **What they do:** AI-powered clinical intelligence platform. They focus on "intelligent prior authorization" by aligning clinical data with payer policies in real-time [29].
*   **Customers:** Health plans (e.g., Highmark Health) and large health systems (e.g., Allegheny Health Network) [29, 30].
*   **Valuation:** $750M (Series C, May 2025) [35].
*   **The Gap:** They sell top-down to payers and massive IDNs (Integrated Delivery Networks). They do not sell bottom-up to independent ASCs. Their implementation cycles are massive.

### Infinitus Systems
*   **What they do:** Voice AI. Their "Eva" assistant literally calls payers on the phone to check benefits, verify PA requirements, and get status updates [42].
*   **Customers:** Physician groups, health systems [42].
*   **Valuation:** Raised $105M total (Series C, April 2023) [44].
*   **The Gap:** They automate the *follow-up* phone calls, not the initial clinical extraction and narrative generation. They solve the "waiting on hold" problem, not the "digging through a 40-page PDF to find the MRI date" problem.

### Rhyme (formerly PriorAuthNow / Olive AI)
*   **What they do:** Network connecting payers and providers for real-time PA decisions [36].
*   **Customers:** Hospitals and physician practices [36].
*   **Valuation:** Raised $57M+ (survived the Olive AI collapse) [38, 40].
*   **The Gap:** Rhyme relies on direct integrations with payer systems to work effectively. If a payer isn't in their network, the value proposition drops significantly.

### Abridge & Regard
*   **What they do:** Ambient clinical documentation (Abridge) and diagnostic intelligence (Regard). Abridge is moving into PA via a partnership with Availity [17, 46].
*   **Customers:** Large health systems (Abridge serves Johns Hopkins, Mayo Clinic) [49].
*   **Valuation:** Abridge is valued at $850M+ [52]. Regard raised $15.3M Series A [48].
*   **The Gap:** Their core competency is writing the initial clinical note while the doctor is in the room. They are upstream of the billing coordinator.

## 3. CortaLoom's Differentiation & The White Space

The market map reveals a massive, unaddressed white space that CortaLoom is perfectly positioned to capture.

### The White Space: Independent & Mid-Market ASCs
*   **Incumbents (Waystar, Availity):** Serve ASCs, but with clunky, generalized administrative tools that don't understand clinical nuance.
*   **AI Entrants (Cohere, Abridge):** Serve massive health systems and payers with multi-month enterprise deployments.
*   **CortaLoom:** Built specifically for the ASC billing coordinator. A bottom-up, self-serve, specialty-specific extraction engine.

### CortaLoom's Specific Differentiation

1.  **Specialty-Specific "Spoke" Architecture:** Competitors try to build a generalized PA tool for every CPT code in medicine. CortaLoom builds deep, specialty-specific extraction schemas (starting with Ortho and Spine). This means CortaLoom actually knows that an MRI older than 6 months will trigger a denial for a lumbar fusion—a generalized tool does not.
2.  **The "Payer Readiness Score":** Waystar will happily submit a claim that is missing conservative treatment documentation and let it get denied 10 days later. CortaLoom catches the missing criteria *before* submission, guiding the coordinator to fix it. This is a paradigm shift from "submission automation" to "denial prevention."
3.  **Operator-Centric UX:** Availity is built for data routing. CortaLoom is built for the human operator. Features like the "Surgical Case Card," plain-English AI summaries, and the time-saved counter treat the billing coordinator as the primary user, not an afterthought.
4.  **No Payer Integration Required:** Rhyme and Cohere rely on deep integrations with payer systems. CortaLoom extracts the data and generates the narrative, which the coordinator can then submit via whatever portal the payer requires (or export as a PDF). CortaLoom provides value immediately, regardless of the payer's technological maturity.

## 4. M&A Landscape & Exit Positioning

The ultimate goal for CortaLoom is acquisition. The competitive landscape dictates the likely acquirers:

*   **The RCM Roll-Ups (Waystar, R1 RCM):** They need to inject real clinical AI into their aging platforms. Buying CortaLoom gives them a best-in-class extraction engine for high-value surgical specialties that they can cross-sell to their massive existing ASC customer base.
*   **The Payer-Side Networks (Availity):** Availity wants to own the entire transaction lifecycle. Buying CortaLoom gives them a tool that makes providers *want* to use their network, rather than feeling forced to.
*   **EHR/Practice Management Systems (SIS, ModMed):** Systems that specifically target ASCs need embedded PA capabilities to prevent churn to standalone RCM vendors.

By focusing relentlessly on the Ortho/Spine ASC niche and building a modular "Hub and Spoke" architecture, CortaLoom becomes an easily digestible acquisition target for any of these major players looking to upgrade their clinical AI capabilities.

---
### References
[1] Waystar Authorization Manager
[2] Waystar Auth Accelerate
[4] Waystar ASC Solutions
[8] Waystar IPO (June 2024)
[15] Availity Essentials
[17] Availity and Abridge Partnership
[29] Cohere Health Platform
[35] Cohere Health Series C
[36] Rhyme (PriorAuthNow)
[42] Infinitus Systems (Eva)
[49] Abridge Clinical AI
