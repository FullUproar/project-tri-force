# CortaLoom Product Specification

**Product Name:** CortaLoom (formerly Project Tri-Force)
**Domain:** cortaloom.ai
**Repo:** github.com/FullUproar/project-tri-force
**Current Phase:** Phase 1 — ASC Prior Auth Trojan Horse
**Current Goal:** Production-ready DICOM/PDF/clinical note ingestion engine with prior auth dashboard.

## What CortaLoom Is

A universal B2B AI data middleware platform that normalizes fragmented, proprietary clinical data. The initial beachhead is orthopaedic ASC prior authorization — automating the extraction of structured data from surgeon notes, robotic reports, and DICOM imaging to generate payer submission narratives.

The long-term play: expand into Veterinary and Dental verticals via the same hub-and-spoke architecture.

## Tech Stack (Actual — as of 2026-03-31)

| Layer | Technology | Notes |
|---|---|---|
| Frontend | Next.js 15 (App Router), React 19, Tailwind v4, TanStack Query | Deployed on Vercel |
| Backend | FastAPI (Python 3.13), async everywhere | Not yet deployed — local dev only |
| Database | Neon PostgreSQL (serverless) + pgvector | Migrations via Alembic, 4 tables live |
| ORM | SQLAlchemy 2.0 (async) + asyncpg | Mapped column syntax |
| Storage | MinIO (local dev) / S3 (production TBD) | boto3 abstraction layer |
| AI/LLM | Anthropic Claude Sonnet only (via LangChain) | Structured output for extraction, free-form for narrative |
| PHI Scrubbing | Regex + Microsoft Presidio (dual-pass) | ScrubbedText NewType enforces safety |
| Medical Imaging | pydicom | DICOM metadata extraction + Safe Harbor de-identification |
| PDF Parsing | pypdf | Text extraction from robotic report PDFs |
| Auth | None yet | Phase 2: Clerk or API key auth |

## Project Structure

```
triforce/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Pydantic v2 Settings (TF_ prefix)
│   │   ├── api/v1/
│   │   │   ├── ingest.py        # 3 ingestion endpoints + SSE status
│   │   │   └── extraction.py    # Narrative generation endpoint
│   │   ├── models/
│   │   │   ├── database.py      # SQLAlchemy models (4 tables)
│   │   │   └── schemas.py       # Pydantic schemas + ScrubbedText
│   │   ├── services/
│   │   │   ├── dicom_service.py
│   │   │   ├── phi_scrubber.py
│   │   │   ├── pdf_parser.py
│   │   │   ├── storage.py
│   │   │   └── llm/
│   │   │       ├── extraction.py   # Claude structured output chain
│   │   │       ├── narrative.py    # Claude narrative generation
│   │   │       └── prompts.py
│   │   └── core/
│   │       ├── db.py, logging.py, security.py
│   ├── alembic/                 # Database migrations
│   ├── tests/                   # pytest + synthetic fixtures
│   └── .env                     # Local secrets (not committed)
├── frontend/
│   ├── src/
│   │   ├── app/page.tsx         # Main dashboard
│   │   ├── components/          # FileDropzone, PriorAuthForm, NarrativePanel, ProcessingStatus
│   │   ├── hooks/               # useFileUpload, useProcessingStatus (SSE)
│   │   └── lib/api.ts           # Typed API client
├── docker-compose.yml           # PostgreSQL + MinIO + backend + frontend
└── Makefile
```

## Database Schema (Live in Neon)

- `ingestion_jobs` — tracks every uploaded file (DICOM, note, PDF) with status and metadata
- `extraction_results` — structured OrthoPriorAuthData extracted by Claude
- `payer_narratives` — generated prior auth narratives with model/prompt versioning
- `clinical_note_embeddings` — pgvector table (schema defined, populated in Phase 2)

## API Endpoints (Implemented)

- `POST /api/v1/ingest/dicom` — DICOM upload, metadata extraction, PHI stripping
- `POST /api/v1/ingest/clinical-note` — Text file or JSON body
- `POST /api/v1/ingest/robotic-report` — PDF upload with text extraction
- `GET /api/v1/ingest/jobs/{id}` — Job status + extraction results
- `GET /api/v1/ingest/jobs/{id}/status` — SSE real-time processing updates
- `POST /api/v1/extraction/{id}/narrative` — Generate payer narrative
- `GET /health` — Health check

## Architecture Decisions (Do Not Override)

1. **Anthropic-only** — no OpenAI dependency. Claude handles both extraction and narrative.
2. **ScrubbedText NewType** — LLM services only accept PHI-scrubbed text. This is a type-level safety guard.
3. **SSE for real-time status** (not WebSocket) — simpler, unidirectional, native browser support.
4. **BackgroundTasks for processing** (not Celery) — sufficient for MVP. Celery is Phase 2.
5. **No PHI in logs, errors, or LLM calls** — enforced architecturally, not by convention.

## What's Built vs. What's Not

| Feature | Status |
|---|---|
| Backend API (all 6 endpoints) | Built |
| DICOM ingestion + de-identification | Built |
| PHI scrubber (regex + Presidio) | Built |
| PDF parsing | Built |
| LLM extraction (Claude structured output) | Built |
| Narrative generation (Claude) | Built |
| SSE status streaming | Built |
| Frontend dashboard (upload + form + narrative) | Built |
| Database schema + migrations | Built, live in Neon |
| MinIO local storage | Needs Docker |
| Backend deployment (Vercel/Railway/Fly) | Not started |
| Authentication | Not started (Phase 2) |
| Multi-tenancy | Not started (Phase 2) |
| Vector search on clinical notes | Schema ready, not populated |
| Vet/Dental spokes | Not started (Phase 2+) |

## Core Rules for Manus

1. Only create issues that move us toward the **Current Goal** above.
2. Break features into atomic, independently testable PRs. One issue = one PR.
3. Always include the `[Claude-Ready]` tag in issue titles when ready for implementation.
4. **Do not change the tech stack** without creating a `[Needs-Review]` issue first.
5. **Do not create issues that require schema changes** without specifying the exact migration.
6. Reference specific files and functions in the Technical Approach section.
7. Keep issue scope small — if it touches more than 5 files, break it up.
8. Priority labels: `P0` (blocking), `P1` (critical path), `P2` (nice to have).
