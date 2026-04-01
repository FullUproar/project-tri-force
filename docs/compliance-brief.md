# CortaLoom Compliance Brief: 2026 Regulatory Landscape

This document outlines the specific regulatory requirements and compliance obligations for CortaLoom, a B2B AI middleware platform for orthopaedic Ambulatory Surgery Centers (ASCs). The analysis covers HIPAA, FDA Software as a Medical Device (SaMD) exemptions, state AI laws, and B2B outreach compliance based on the regulatory environment as of early 2026.

## 1. HIPAA Compliance for AI SaaS (2026 Updates)

The Health Insurance Portability and Accountability Act (HIPAA) Security Rule has undergone significant updates in 2025 and 2026, shifting from flexible guidelines to prescriptive, auditable requirements for SaaS vendors handling electronic Protected Health Information (ePHI) [1]. CortaLoom acts as a Business Associate (BA) to its ASC customers (Covered Entities) because it receives and processes ePHI (clinical notes, DICOM images) [2].

### Key 2026 Security Rule Requirements

The modernized Security Rule requires operationalized proof of compliance rather than mere policy documentation [1]:

*   **Multi-Factor Authentication (MFA):** Must be enforced broadly, especially for administrative accounts, with documented exceptions [1].
*   **Encryption:** Must be the default for data in transit and at rest, with defined key ownership [1].
*   **Vulnerability Management:** Scanning and penetration testing must occur on a strict schedule, with findings tracked to closure [1].
*   **Data Mapping:** Organizations must maintain a formal inventory and map of where ePHI resides, how it moves, and which vendors access it [1].
*   **Business Associate Agreements (BAAs):** Any AI vendor processing PHI must operate under a robust BAA that outlines permissible data use, including strict limitations on using PHI to train AI models unless properly de-identified [3].

### CortaLoom Implementation Gaps

While CortaLoom currently implements PHI scrubbing via Microsoft Presidio, the following gaps remain:

*   **Data Retention and Purge Policy:** A documented mechanism to automatically purge ePHI after a defined period, complying with the 7-year retention rule or customer-specific BAA terms.
*   **Encryption Key Management:** Documented procedures for managing encryption keys for data at rest in Neon Postgres and S3/R2 storage.
*   **BAA Management:** A system to track and execute BAAs per tenant organization before allowing them to upload ePHI.

## 2. FDA Regulation: SaMD and Clinical Decision Support

The FDA regulates software that meets the definition of a medical device (SaMD). However, the 21st Century Cures Act and subsequent FDA guidance exclude certain Clinical Decision Support (CDS) software from this definition [4] [5].

### The Non-Device CDS Exemption

To qualify for the CDS exemption and avoid FDA 510(k) clearance, software must meet four specific criteria [4] [5]:

1.  **Not intended to acquire, process, or analyze a medical image or a signal from an in vitro diagnostic device or a pattern or signal from a signal acquisition system.**
2.  **Intended for the purpose of displaying, analyzing, or printing medical information about a patient or other medical information (such as peer-reviewed clinical studies and clinical practice guidelines).**
3.  **Intended for the purpose of supporting or providing recommendations to a health care professional about prevention, diagnosis, or treatment of a disease or condition.**
4.  **Intended for the purpose of enabling the health care professional to independently review the basis for such recommendations that such software presents so that it is not the intent that such health care professional rely primarily on any of such recommendations to make a clinical diagnosis or treatment decision regarding an individual patient.**

### CortaLoom's Regulatory Positioning

CortaLoom is designed as an administrative and operational tool—specifically, a prior authorization extraction and narrative generation engine. It does *not* diagnose patients, recommend treatments, or analyze medical images for diagnostic purposes. It parses existing clinical notes and DICOM metadata to populate administrative forms.

**Conclusion:** CortaLoom falls squarely outside the definition of a medical device because its primary function is administrative (prior authorization), not diagnostic or therapeutic. It does not require FDA 510(k) clearance, provided its marketing and intended use remain strictly focused on administrative workflow automation.

## 3. State AI and Privacy Laws (The Texas TRAIGA Impact)

In 2026, state-level AI regulation has accelerated. The most critical law for CortaLoom is the Texas Responsible Artificial Intelligence Governance Act (TRAIGA), effective January 1, 2026 [6] [7].

### Texas TRAIGA Requirements

TRAIGA imposes specific disclosure obligations on healthcare providers and AI developers [6] [7]:

*   **Provider Disclosure:** Healthcare providers must provide written disclosure to patients that an AI system is being used in connection with their care [6].
*   **Developer Obligations:** AI deployers and developers must provide clear and conspicuous disclosure to consumers regarding the use of AI [6].

### CortaLoom Implementation Gaps

Because CortaLoom targets independent ASCs (many of which may operate in Texas or treat Texas residents), the platform must support compliance with TRAIGA:

*   **Patient Disclosure Support:** CortaLoom should provide ASCs with standardized disclosure templates or automated patient notification features to help them comply with TRAIGA's written disclosure requirement.
*   **Transparency Reporting:** The platform must clearly document its AI methodology (e.g., the use of Claude Sonnet) and limitations to satisfy developer transparency obligations.

## 4. B2B Outreach Compliance (CAN-SPAM)

CortaLoom's growth strategy relies on automated, AI-personalized cold email outreach to ASC administrators. This activity is governed by the CAN-SPAM Act in the United States [8].

### CAN-SPAM Requirements for B2B Cold Email

CAN-SPAM is an opt-out law, meaning prior consent is not required for B2B cold emails, provided specific rules are followed [8] [9]:

*   **No Misleading Headers:** "From," "To," "Reply-To," and routing information must be accurate and identify the sender [8].
*   **Accurate Subject Lines:** The subject line must accurately reflect the content of the message [8].
*   **Identify as an Ad:** The message must be clearly identified as an advertisement or solicitation (though this is often interpreted flexibly in B2B contexts) [8].
*   **Location:** The email must include a valid physical postal address [8].
*   **Opt-Out Mechanism:** The email must include a clear, conspicuous, and functional way for recipients to opt out of future emails, and opt-out requests must be honored within 10 business days [8].

### CortaLoom Implementation Gaps

The automated outreach pipeline currently being built by Claude Code must incorporate these compliance features:

*   **Physical Address:** The email generation script (`04_generate_emails.py`) must append CortaLoom's physical address to every email signature.
*   **Opt-Out Link:** The sending script (`05_send_emails.py`) must include a functional unsubscribe link or clear instructions (e.g., "Reply 'unsubscribe' to stop receiving these emails").
*   **Suppression List:** The pipeline must maintain a suppression list of opted-out domains/emails and check against it before sending.

## References

[1] Sprinto. "HIPAA Updates for 2026: Compliance Deadlines and Actions." https://sprinto.com/blog/hipaa-updates-2026/
[2] Paubox. "When does AI become a business associate under HIPAA?" https://www.paubox.com/blog/when-does-ai-become-a-business-associate-under-hipaa
[3] Foley & Lardner LLP. "HIPAA Compliance for AI in Digital Health: What Privacy Officers Need to Know." https://www.foley.com/insights/publications/2025/05/hipaa-compliance-ai-digital-health-privacy-officers-need-know/
[4] FDA. "Clinical Decision Support Software - Guidance for Industry and Food and Drug Administration Staff." https://www.fda.gov/media/109618/download
[5] FDA. "Clinical Decision Support Software." https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software
[6] Manatt, Phelps & Phillips, LLP. "Health AI Policy Tracker." https://www.manatt.com/insights/newsletters/health-highlights/manatt-health-health-ai-policy-tracker
[7] JD Supra. "New Year, New AI Rules: Healthcare AI Laws Now in Effect." https://www.jdsupra.com/legalnews/new-year-new-ai-rules-healthcare-ai-9758831/
[8] FTC. "CAN-SPAM Act: A Compliance Guide for Business." https://www.ftc.gov/business-guidance/resources/can-spam-act-compliance-guide-business
[9] InfoTanks Media. "Is Cold Email Legal In 2025: B2B Compliance & Risk Guide." https://www.iinfotanks.com/is-cold-email-legal-in-2025-b2b-compliance-risk-guide/
