# CortaLoom Payer Policy Intelligence System

## The Strategic Insight
Most prior auth tools treat payer policy as a static lookup table. CortaLoom's competitive advantage is treating it as a **live, monitored data feed** — and making that currency visible to the user as a trust signal.

When a billing coordinator sees "UHC Lumbar Fusion Policy — Last verified April 1, 2026 — No changes since March 15" next to a Green Payer Readiness Score, she doesn't just trust the result. She trusts the *system*. That trust is the moat.

---

## The Three Layers of the System

### Layer 1: The Policy Database (The Foundation)
A structured, versioned database of payer prior auth criteria. Each record contains:
- **Payer** (UHC, Aetna, BCBS, Cigna, Humana)
- **Procedure** (Lumbar Fusion, Knee Replacement, Shoulder Scope, etc.)
- **Criteria** (structured JSON: PT duration required, imaging recency, diagnosis codes, etc.)
- **Source URL** (direct link to the payer's published LCD or Clinical Policy Bulletin)
- **Version** (incrementing integer)
- **Effective Date** (when this version of the policy became active)
- **Verified Date** (when CortaLoom last confirmed this is current)
- **Changelog** (human-readable summary of what changed from the previous version)

### Layer 2: The Policy Monitor (The Engine)
An automated background job that runs on a weekly schedule and checks each payer's policy source URL for changes.

**How it works:**
1. The monitor fetches the current version of each payer's LCD or Clinical Policy Bulletin PDF.
2. It computes a hash of the document content and compares it to the stored hash.
3. If the hash has changed, it triggers the **Policy Diff Engine**.

**The Policy Diff Engine:**
When a change is detected, the LLM is used to:
1. Summarize what changed in plain English (e.g., "Aetna now requires 8 weeks of PT instead of 6 weeks for lumbar fusion").
2. Identify which specific criteria fields in the database need to be updated.
3. Flag the change as **Minor** (e.g., wording clarification), **Moderate** (e.g., documentation requirement added), or **Major** (e.g., procedure now requires pre-approval where it previously did not).

All Major and Moderate changes require a human review flag before going live in the Payer Readiness Score engine.

### Layer 3: The Trust Indicators (The User-Facing Layer)
This is the selling point. Every place the Payer Readiness Score appears, it must be accompanied by a trust signal that shows the user the policy is current.

**The Policy Freshness Badge:**
A small, unobtrusive badge next to every payer name in the Surgical Case Card:
- 🟢 **Verified [Date]** — Policy confirmed current within the last 30 days.
- 🟡 **Verified [Date]** — Policy confirmed current 31–90 days ago. Verification pending.
- 🔴 **Needs Review** — Policy has not been verified in over 90 days, or a change was detected and is pending human review.

**The Policy Changelog Feed:**
A dedicated "Policy Updates" section in the app (accessible from the nav bar) that shows a reverse-chronological list of all policy changes detected, with plain-English summaries. Example entries:
- *"April 1, 2026 — UHC Lumbar Fusion: Conservative treatment requirement updated from 6 weeks to 8 weeks of documented physical therapy."*
- *"March 15, 2026 — Aetna Knee Replacement: No changes detected. Policy confirmed current."*

**The In-Context Alert:**
If a policy has changed since the last time a case was processed, and the change affects the criteria used in that case's Payer Readiness Score, the system must display a banner: *"Heads up: Aetna updated their Lumbar Fusion policy on April 1. Your Payer Readiness Score has been recalculated. Review the changes."*

---

## The Selling Points (For Reps and the Landing Page)

This system generates three distinct selling points that no competitor currently offers:

1. **"Our payer policies are verified weekly, not annually."** Most tools rely on manually-maintained rule sets that go stale. CortaLoom's policies are live.
2. **"We tell you when the rules change before you get a denial."** The changelog feed is a proactive alert system, not a reactive fix.
3. **"Every Payer Readiness Score shows you exactly when it was last verified."** Transparency builds trust. Trust drives retention.

---

## Implementation Sequence for Claude

This system should be built in three phases, in order:

**Phase A (Foundation):** Build the `PayerPolicy` database model with versioning and the seed data for the top 5 payers / top 10 procedures. This replaces the current hard-coded rules.

**Phase B (Monitor):** Build the weekly background job that checks source URLs for changes and runs the Policy Diff Engine. Start with manual review of all detected changes.

**Phase C (UI):** Build the Policy Freshness Badge, the Policy Changelog Feed page, and the In-Context Alert banner.

Phase A is a dependency for everything else in the system. It should be prioritized immediately after the current sprint.
