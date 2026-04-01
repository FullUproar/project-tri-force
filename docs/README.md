# CortaLoom Strategic Documents

This directory contains strategic and architectural documents for the CortaLoom platform. These are **read-only reference documents** for Claude Code — do not modify them unless explicitly instructed.

## Legal Entity

**CortaLoom AI, Inc.** is a C corporation incorporated in the state of Indiana. All legal documents, BAA templates, email footers, and contract strings must use this full legal name. The product UI uses the short form **CortaLoom**.

## Document Index

| Document | Purpose | Last Updated |
|---|---|---|
| [platform-roadmap.md](./platform-roadmap.md) | The definitive Hub & Spoke platform roadmap. Defines all Spokes, their dependency order, and the strict unlock criteria required before advancing to the next phase. **This is the north star for all architectural decisions.** | 2026-04-01 |
| [tri-force-strategy.md](./tri-force-strategy.md) | Strategic analysis of the Tri-Force thesis (Ortho + Dental + Vet). Explains why a unified extraction engine is wrong and why the Hub & Spoke model is correct. Includes market sizing for each vertical. | 2026-04-01 |
| [compliance-brief.md](./compliance-brief.md) | Full HIPAA, FDA, Texas TRAIGA, and CAN-SPAM compliance audit. Lists every compliance gap and the corresponding GitHub issue number. | 2026-04-01 |
| [ux-brief.md](./ux-brief.md) | Wow Factor UX Brief. Defines the operator persona, the "wow" moments, and the exact UI specifications for the Surgical Case Card (#215), Time Saved counter (#214), Payer Readiness Score (#218), and "What the AI Found" panel (#220). **Read before implementing any of those issues.** | 2026-04-01 |
| [payer-policy-brief.md](./payer-policy-brief.md) | Payer Policy Intelligence Brief. Top 5 commercial payer prior auth requirements for ortho/spine (UHC, Aetna, BCBS, Cigna, Humana). Defines the data model for the payer policy scraper (#201) and payer-specific templates (#205). **Read before implementing #201 or #205.** | 2026-04-01 |

## Key Architectural Decisions (Do Not Override)

The following decisions are locked and must not be revisited without explicit founder approval:

1. **`vertical` enum on `Organization`** — The single source of truth for all routing decisions. Never hardcode a vertical in application logic.
2. **JSONB extraction storage with `schema_version`** — Allows all verticals to share the same database table without migrations.
3. **Prompt Registry pattern** — Prompts are always loaded from `backend/app/prompts/registry.py`, never hardcoded.
4. **PHI scrubbing before LLM** — All documents must pass through Presidio before reaching the LLM. No exceptions.

## Legal Name Usage Rules

| Context | Correct String |
|---------|---------------|
| Legal documents, BAAs, contracts | **CortaLoom AI, Inc.** |
| Product UI (app name, page titles) | **CortaLoom** |
| Email footers (CAN-SPAM compliance) | **CortaLoom AI, Inc.** |
| `package.json` / `pyproject.toml` name fields | `cortaloom-ai` |
| Copyright notices | **© 2026 CortaLoom AI, Inc.** |

See issue #227 for the full audit checklist.
