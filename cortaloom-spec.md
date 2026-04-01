# CortaLoom Product Specification

**Legal Entity:** CortaLoom AI, Inc. (Indiana C Corporation)
**Domain:** cortaloom.ai
**Current Phase:** Phase 1A — ASC Pilot (Orthopaedics)
**Current Goal:** Onboard 3 paying ASC pilots at $299/month.

## Production Stack (Live)

**Backend** — FastAPI on Railway (`project-tri-force-production.up.railway.app`):
- Python 3.13, FastAPI, SQLAlchemy 2.0 (async), Alembic (7 migrations applied)
- Neon PostgreSQL + pgvector
- Cloudflare R2 (S3-compatible object storage)
- LangChain + Anthropic Claude Sonnet (extraction + narrative)
- Microsoft Presidio + regex (dual-pass PHI scrubbing with ScrubbedText type guard)
- Stripe billing ($299/month subscription)
- Sentry error tracking
- 72 pytest tests passing

**Frontend** — Next.js 15 on Vercel (`cortaloom.ai`):
- React 19, Tailwind v4, TanStack Query
- Clerk auth (sign-in, sign-up, protected routes, user menu)
- Server-side API proxy (API key never in browser bundle)
- @sentry/nextjs for frontend error tracking
- Playwright E2E tests
- 7 pages: Dashboard, Sign-in, Sign-up, Onboarding, Admin, Analytics, Billing

## What's Built (Complete Feature List)

### Ingestion Pipeline
- POST /ingest/dicom — DICOM metadata extraction + Safe Harbor de-identification
- POST /ingest/clinical-note — text file upload
- POST /ingest/clinical-note/text — JSON body (for demo button)
- POST /ingest/robotic-report — PDF text extraction
- File size validation on all endpoints
- Clinical note minimum length validation

### LLM Pipeline
- Claude Sonnet structured extraction → OrthoPriorAuthData (ICD-10, treatments, implant, robotic, justification, confidence)
- Claude Sonnet narrative generation (payer submission letters)
- LLM call latency logging (no content logged)
- ScrubbedText type guard prevents raw PHI from reaching LLM

### Job Management
- GET /ingest/jobs — paginated job list (tenant-scoped)
- GET /ingest/jobs/{id} — job status + extraction results
- GET /ingest/jobs/{id}/status — SSE real-time updates (DB-backed, survives deploys)
- POST /ingest/jobs/{id}/retry — retry failed jobs
- Stuck job recovery on startup (>10min processing → failed)

### Extraction & Narrative
- POST /extraction/{id}/narrative — generate payer narrative
- PATCH /extraction/{id}/outcome — track approved/denied/pending/appealed
- GET /extraction/{id}/export/pdf — formatted PDF with AI disclosure
- GET /share/{id} — public read-only link (no auth, UUID capability token)
- GET /disclosure — TRAIGA AI disclosure text

### Analytics
- GET /analytics/outcomes — approval rate, outcome breakdown
- GET /analytics/usage — total cases, avg confidence, hours saved

### Admin
- POST /admin/organizations — create ASC org with auto-generated API key
- GET /admin/organizations — list all orgs with usage stats
- POST /admin/organizations/{id}/sign-baa — mark BAA as signed

### Billing
- POST /billing/checkout — Stripe Checkout session
- GET /billing/status — subscription status
- POST /billing/portal — Stripe Customer Portal
- POST /billing/webhook — Stripe subscription lifecycle events

### Auth & Security
- Clerk auth (sign-in, sign-up, protected routes)
- Multi-tenancy (Organization model, hashed API keys, tenant_id on all tables)
- BAA enforcement (403 until baa_signed_at set)
- Security headers (HSTS, X-Frame-Options, CSP, etc.)
- CORS restricted to cortaloom.ai + localhost
- HIPAA audit logging (audit_log table)
- Data retention purge (configurable, default 90 days)
- Sentry error tracking (send_default_pii=False)

### Frontend Features
- Drag-and-drop file upload (DICOM, PDF, TXT auto-routed)
- "Try Demo" button with sample clinical note
- Surgical case card (diagnosis, stats grid, implant, outcome)
- "What the AI Found" plain-English summary
- Payer Readiness Score (0-100% with gap analysis)
- Conservative Treatment Checklist (visual card grid)
- Time-Saved Counter (~44 min saved per extraction)
- ICD-10 code descriptions (30+ common ortho codes)
- Prior Auth Form with confidence badges and outcome tracker
- Narrative panel with copy, download PDF, share link, regenerate
- Job history panel with status dots and click-to-load
- Loading skeletons during processing
- New Case button to reset dashboard
- User avatar with sign-out (Clerk UserButton)

### Compliance Documents
- SECURITY.md — encryption, PHI controls, secret rotation, audit trail
- FDA_POSITIONING.md — non-device CDS exemption analysis
- TRAIGA AI disclosure in all PDF exports

## Database Schema (7 migrations)
- organizations (name, is_active, baa_signed_at, stripe_customer_id, subscription_status)
- api_keys (organization_id, key_hash SHA-256, name, is_active)
- ingestion_jobs (tenant_id, source_type, status, file_key, metadata_json)
- extraction_results (tenant_id, diagnosis_code, treatments, implant, robotic, justification, confidence, outcome, raw_extraction_json)
- payer_narratives (tenant_id, narrative_text, model_used, prompt_version)
- clinical_note_embeddings (tenant_id, chunk_index, content, embedding VECTOR(1536)) — schema ready, Phase 2
- audit_log (tenant_id, action, resource_type, resource_id, request_id, ip_address, metadata_json)

## Core Rules for Manus

1. **Check before filing:** Most features below are already built. Check this spec before creating issues.
2. **No new vendors:** Anthropic only for LLM. Clerk for auth. Stripe for billing. No exceptions without founder approval.
3. **No architecture changes:** Multi-tenancy, ScrubbedText type guard, server-side proxy, and JSONB extraction storage are locked decisions.
4. **Atomic issues:** One PR per issue. If it touches >5 files, break it up.
5. **Docs go in /docs:** Don't modify code files. Strategic documents go in the /docs directory.
6. **Priority labels required:** P0 > P1 > P2. Claude Code works highest priority first.
