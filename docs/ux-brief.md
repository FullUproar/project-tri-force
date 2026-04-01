# CortaLoom Wow Factor UX Brief: The Operator Experience

This document defines the user experience (UX) philosophy and specific UI specifications for the CortaLoom prior authorization platform. It is written specifically for the ASC Prior Authorization Coordinator — the person who will actually use the tool every day.

## The Operator Persona

The ASC Prior Authorization Coordinator is overwhelmed, understaffed, and constantly context-switching. They spend their days:
1. Hunting through dense EMR clinical notes for specific phrases (e.g., "failed 6 weeks of physical therapy").
2. Re-typing identical patient demographics into 5 different payer portals.
3. Waiting on hold for 30+ minutes just to check the status of a pending case.
4. Formatting complex letters of medical necessity.

**Their primary emotion is frustration.** They feel like data-entry clerks, not healthcare professionals.

**The "Wow" Moment:** The wow moment for this user is *not* a flashy animation or a complex dashboard. The wow moment is **relief**. It is the realization that the software has already done the reading, the hunting, and the typing for them. The UX must feel clean, confident, and highly intentional [1].

## Key UI Components (Specifications for Claude Code)

### 1. The "Time Saved" Counter (Issue #214)

This is the most important psychological element in the application. It explicitly quantifies the value of the platform to the user in real-time.

*   **Placement:** Prominent, persistent placement in the top navigation bar or the main dashboard header.
*   **Format:** A running tally. E.g., `⏱️ 14 hours saved this week` or `⏱️ 2.5 hours saved today`.
*   **Logic:** Every time an extraction is completed, the system should add a predefined amount of time to the counter (e.g., 45 minutes for a spine case, 30 minutes for a knee case) representing the manual effort avoided.
*   **UX Pattern:** When a new case finishes extracting, the counter should briefly highlight or pulse (like a Slack notification) to draw attention to the newly saved time.

### 2. The Surgical Case Card (Issue #215)

The Surgical Case Card is the primary view for a single prior authorization request. It replaces the fragmented view of multiple EMR tabs and PDF documents.

*   **Layout:** A two-column or split-pane design.
    *   **Left Pane (The Source):** The original uploaded documents (PDFs, clinical notes) with a built-in viewer.
    *   **Right Pane (The Output):** The structured data extracted by the LLM.
*   **Interaction:** Clicking a piece of extracted data in the Right Pane (e.g., "Failed conservative treatment: PT") should ideally highlight or scroll to the exact sentence in the original document in the Left Pane. This builds trust in the AI's accuracy.
*   **Cleanliness:** The interface should feel as clean and uncluttered as a Stripe dashboard. No unnecessary borders, drop shadows, or dense text blocks. Use whitespace generously.

### 3. The Payer Readiness Score (Issue #218)

This feature shifts the coordinator from a reactive state (waiting for a denial) to a proactive state.

*   **Visual Representation:** A clear, color-coded score or status indicator (e.g., a green checkmark for "Ready to Submit," a yellow warning for "Missing Information," a red alert for "High Risk of Denial").
*   **Actionable Gap Analysis:** If the score is not "Ready," the UI must explicitly list *why*. E.g., "Missing: Documentation of 6 weeks of physical therapy."
*   **TurboTax Pattern:** The UI should guide the user step-by-step to resolve the gaps, similar to how TurboTax guides a user through tax deductions [1].

### 4. "What the AI Found" Summary Panel (Issue #220)

Instead of just presenting a finished letter of medical necessity, the system should explain its reasoning in plain English.

*   **Format:** A brief, bulleted summary at the top of the Case Card.
*   **Content:** "Found documentation of severe osteoarthritis. Found evidence of failed NSAID therapy. *Could not find* recent MRI results."
*   **Purpose:** This builds immediate trust. The coordinator doesn't have to guess if the AI read the whole chart; the AI tells them exactly what it saw.

## Summary

The CortaLoom UX must prioritize speed, clarity, and trust. By explicitly quantifying time saved, providing clear source attribution for extracted data, and proactively identifying missing information, the platform transforms the coordinator's workflow from a frustrating administrative burden into a streamlined, guided process.

## References

[1] User Persona Research. "ASC Prior Authorization Coordinator Workflow and UX." /home/ubuntu/parallel_research.json
