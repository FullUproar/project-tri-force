# CortaLoom Strategic Documents

This directory contains strategic and architectural documents for the CortaLoom platform. These are **read-only reference documents** for Claude Code — do not modify them unless explicitly instructed.

| Document | Purpose | Last Updated |
|---|---|---|
| [platform-roadmap.md](./platform-roadmap.md) | The definitive Hub & Spoke platform roadmap. Defines all Spokes, their dependency order, and the strict unlock criteria required before advancing to the next phase. **This is the north star for all architectural decisions.** | 2026-04-01 |
| [tri-force-strategy.md](./tri-force-strategy.md) | Strategic analysis of the Tri-Force thesis (Ortho + Dental + Vet). Explains why a unified extraction engine is wrong and why the Hub & Spoke model is correct. Includes market sizing for each vertical. | 2026-04-01 |
| [compliance-brief.md](./compliance-brief.md) | Full HIPAA, FDA, Texas TRAIGA, and CAN-SPAM compliance audit. Lists every compliance gap and the corresponding GitHub issue number. | 2026-04-01 |

## Key Architectural Decisions (Do Not Override)

The following decisions are locked and must not be revisited without explicit founder approval:

1. **`vertical` enum on `Organization`** — The single source of truth for all routing decisions. Never hardcode a vertical in application logic.
2. **JSONB extraction storage with `schema_version`** — Allows all verticals to share the same database table without migrations.
3. **Prompt Registry pattern** — Prompts are always loaded from `backend/app/prompts/registry.py`, never hardcoded.
4. **PHI scrubbing before LLM** — All documents must pass through Presidio before reaching the LLM. No exceptions.
