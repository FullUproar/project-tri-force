# CortaLoom Product Specification

**Current Phase:** Phase 1 - ASC Prior Auth Trojan Horse
**Current Goal:** Build the DICOM/PDF ingestion engine and basic UI dashboard for orthopaedic surgical reports.

## Actual Tech Stack
This reflects what is currently scaffolded in the repository.

**Backend (`/backend`):**
- **Framework:** FastAPI (Python 3.11+)
- **Database:** Neon PostgreSQL via SQLAlchemy (asyncpg) + pgvector
- **Migrations:** Alembic
- **AI/LLM:** LangChain + Anthropic Claude (`langchain-anthropic`)
- **Data Parsing:** `pydicom` (DICOM), `pypdf` (PDF)
- **PHI Scrubbing:** Microsoft Presidio (`presidio-analyzer`, `presidio-anonymizer`)
- **Testing:** pytest, pytest-asyncio, testcontainers[postgres]

**Frontend (`/frontend`):**
- **Framework:** Next.js 15.0+ (App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS 4.0+, `clsx`, `tailwind-merge`
- **UI Components:** React 19.0+, Lucide React icons
- **State/Data:** React Query (`@tanstack/react-query`)
- **Forms:** React Hook Form + Zod validation
- **File Upload:** React Dropzone

## Core Rules for Manus (The PM/Architect)
1. **No Hallucinations:** Only specify features that fit within the exact stack listed above. Do not introduce new ORMs, auth providers, or LLM vendors without explicit founder approval.
2. **Atomic Issues:** Break large features into small, testable PRs (e.g., "Build UI component" -> "Wire API endpoint" -> "Integrate DB").
3. **Issue Formatting:** Always use the `.github/ISSUE_TEMPLATE/claude_task.md` format.
4. **Prioritization:** Always assign priority labels (P0, P1, P2) to issues so Claude Code knows what to pull first.
5. **Quality Gates:** Ensure acceptance criteria include specific tests (e.g., "pytest passes for new endpoint").
