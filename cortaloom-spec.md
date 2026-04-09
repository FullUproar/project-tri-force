# CortaLoom Product Specification

**Legal Entity:** CortaLoom AI, Inc. (Indiana C Corporation)
**Domain:** cortaloom.ai
**Current Phase:** Phase 1B — Payer Intelligence Beta
**Current Goal:** Onboard 3 paying ASC pilots at $299/month with payer-specific narrative generation.

## Production Stack (Live)

**Backend** — FastAPI on Railway (`project-tri-force-production.up.railway.app`):
- Python 3.13, FastAPI, SQLAlchemy 2.0 (async), Alembic (14 migrations applied)
- Neon PostgreSQL + pgvector
- Cloudflare R2 (S3-compatible object storage)
- LangChain + Anthropic Claude Sonnet (extraction + narrative with RAG + citations)
- Microsoft Presidio + regex (dual-pass PHI scrubbing with ScrubbedText type guard)
- Stripe tiered billing (Starter $149 / Professional $299 / Enterprise $499)
- Sentry error tracking
- 96+ pytest tests passing

**Frontend** — Next.js 15 on Vercel (`cortaloom.ai`):
- React 19, Tailwind v4, TanStack Query
- Clerk auth (sign-in, sign-up, protected routes, user menu)
- Server-side API proxy (API key never in browser bundle)
- @sentry/nextjs for frontend error tracking
- Playwright E2E tests
- 8 pages: Dashboard, Sign-in, Sign-up, Onboarding, Admin, Analytics, Billing, Policies

## What's Built (Complete Feature List)

### Ingestion Pipeline
- POST /ingest/dicom — DICOM metadata extraction + Safe Harbor de-identification
- POST /ingest/clinical-note — text file upload
- POST /ingest/clinical-note/text — JSON body (for demo button)
- POST /ingest/robotic-report — PDF text extraction
- File size validation on all endpoints (500MB max, configurable)
- Clinical note minimum length validation (20 chars)
- Pagination bounds enforced on job listing (limit 1-100, offset >= 0)

### LLM Pipeline
- Claude Sonnet structured extraction → OrthoPriorAuthData (ICD-10, treatments, implant, robotic, justification, confidence)
- Claude Sonnet narrative generation — 3 modes:
  - **Generic** (v1.0): Standard payer submission letter
  - **Payer-Specific** (v2.0-payer): Tailored to specific payer's requirements
  - **Cited** (v3.0-cited): RAG-augmented with inline citation markers [1], [2] referencing policy chunks and clinical data
- LLM call latency logging (no content logged)
- ScrubbedText type guard prevents raw PHI from reaching LLM
- 60-second timeout with 2 retries and exponential backoff

### Payer Intelligence System
- **30 payer policies** seeded: 5 payers (UHC, Aetna, BCBS, Cigna, Humana) × 6 procedures (Total Knee, Total Hip, Lumbar Fusion, Cervical Fusion, SCS, Rotator Cuff)
- **180 policy chunks**: Each policy generates 6 natural-language chunks (Overview, Conservative Treatment, Imaging, Functional, Special Requirements, Submission Info)
- **RAG retrieval**: Chunks retrieved by payer+procedure, injected as numbered reference sources into narrative prompt
- **Citation engine**: Claude outputs inline [N] markers mapped back to source chunks, stored in narrative_citations table
- **ICD-10 → procedure auto-suggestion**: M17→Total Knee, M16→Total Hip, M75→Rotator Cuff, M54/M47/M51/M48→Lumbar Fusion, G89→SCS
- **Payer-specific readiness scoring**: GET /policies/check evaluates extraction data against specific payer criteria
- **Policy document ingestion pipeline**: Heading-aware text chunking for uploaded documents (PDF text extraction ready)
- GET /policies — list active payer policies with filters
- GET /policies/payers — distinct payer names
- GET /policies/procedures — distinct procedures (filterable by payer)
- GET /policies/suggest-procedure — ICD-10 to procedure mapping
- GET /policies/check — readiness check against payer criteria
- POST /policy-docs/seed-chunks — generate chunks from existing policies (admin)
- GET /policy-docs/chunks — browse/filter policy chunks
- GET /citations/{narrative_id} — retrieve citations for a narrative

### Knowledge Graph (Experimental)
- **Node types**: payer, procedure, criterion, diagnosis, treatment, requirement
- **Edge types**: requires, offered_by, treats, modality_of, has_requirement
- Auto-built from existing 30 payer policies (~60 nodes, ~120 edges)
- **Cross-payer intelligence**: Identifies common requirements (all payers agree), unique requirements (payer-specific), and shared requirements (subset of payers)
- Diagnosis-procedure relationships from ICD-10 mapping
- POST /graph/build — build/rebuild graph from policy data (admin)
- GET /graph/requirements — payer+procedure requirement lookup via graph traversal
- GET /graph/insights — cross-payer intelligence (common vs unique requirements)
- GET /graph/stats — node and edge counts by type

### Job Management
- GET /ingest/jobs — paginated job list (tenant-scoped, bounded pagination)
- GET /ingest/jobs/{id} — job status + extraction results (tenant-verified)
- GET /ingest/jobs/{id}/status — SSE real-time updates (tenant-verified, DB-backed, survives deploys)
- POST /ingest/jobs/{id}/retry — retry failed jobs (tenant-verified)
- Stuck job recovery on startup (>10min processing → failed)
- Error messages sanitized — no internal paths or stack traces leaked to users

### Extraction & Narrative
- POST /extraction/{id}/narrative — generate payer narrative (accepts optional payer + procedure for payer-specific + cited mode)
- PATCH /extraction/{id} — override extraction fields (tenant-verified)
- PATCH /extraction/{id}/outcome — track approved/denied/pending/appealed (tenant-verified)
- GET /extraction/{id}/export/pdf — formatted PDF with AI disclosure (tenant-verified)
- GET /share/{id} — public read-only link (no auth, UUID capability token)
- GET /disclosure — TRAIGA AI disclosure text

### Analytics
- GET /analytics/outcomes — approval rate, outcome breakdown (tenant-scoped)
- GET /analytics/usage — total cases, avg confidence, hours saved (tenant-scoped)
- GET /analytics/outcomes-by-diagnosis — outcome rates grouped by ICD-10 code (tenant-scoped)
- GET /analytics/overrides — user override count and AI accuracy proxy (tenant-scoped)

### Admin
- POST /admin/organizations — create ASC org with auto-generated API key
- GET /admin/organizations — list all orgs with usage stats
- POST /admin/organizations/{id}/sign-baa — mark BAA as signed
- POST /admin/load-demo-data — load synthetic demo cases
- GET /me — current org info and role

### Billing
- POST /billing/checkout — Stripe Checkout session (tiered: starter/professional/enterprise)
- GET /billing/status — subscription status + usage metrics + overage tracking
- GET /billing/tiers — available pricing tiers
- POST /billing/budget — set monthly overage budget cap
- POST /billing/portal — Stripe Customer Portal
- POST /billing/webhook — Stripe subscription lifecycle events (signature-verified)
- Usage metering with Stripe meter events for overages
- 80% and 100% usage threshold alerts
- Budget cap enforcement (blocks extraction when cap reached)

### Auth & Security
- Clerk auth (sign-in, sign-up, protected routes)
- Multi-tenancy with full IDOR prevention:
  - Organization model, hashed API keys (SHA-256), tenant_id on all data tables
  - **Every data-access endpoint verifies tenant_id ownership** (returns 404, not 403)
  - 11 cross-tenant isolation tests covering all endpoints
- BAA enforcement (403 until baa_signed_at set)
- Admin role checking (is_admin flag on Organization)
- Security headers (HSTS, X-Frame-Options, CSP, X-Content-Type-Options, Referrer-Policy, Permissions-Policy)
- CORS restricted to cortaloom.ai + localhost
- HIPAA audit logging (audit_log table with tenant_id traceability)
- Data retention purge (configurable, default 90 days jobs / 7 years audit)
- Sentry error tracking (send_default_pii=False)
- Rate limiting (120/min default, 30/min ingestion)
- Startup validation blocks production with default API key

### Frontend Features
- Drag-and-drop file upload (DICOM, PDF, TXT auto-routed)
- "Try Demo" button with sample clinical note (with error handling)
- Surgical case card (diagnosis, stats grid, implant, outcome)
- "What the AI Found" plain-English summary
- **Payer selector dropdown** — choose insurance company + procedure
- **Payer-specific Readiness Score** — checks against real payer criteria when payer selected, generic 7-point checklist otherwise
- **Inline citations** — clickable [N] markers in narrative with hover tooltips showing claim, source type, and source text
- **Sources panel** — lists all citations below narrative with type badges and source details
- **Payer badge** on narrative panel showing which payer the narrative was tailored for
- Conservative Treatment Checklist (visual card grid)
- Time-Saved Counter (~44 min saved per extraction)
- ICD-10 code descriptions (30+ common ortho codes)
- Prior Auth Form with confidence badges and outcome tracker
- Narrative panel with copy, download PDF, share link, regenerate
- "Generate {Payer}-Specific Narrative" button when payer selected
- Job history panel with status dots and click-to-load
- Loading skeletons during processing
- New Case button (resets payer/procedure selection)
- Error states shown to user (PDF export, demo, narrative generation failures)
- **Policy Viewer page** (/policies) with payer/procedure filters and chunk browsing
- User avatar with sign-out (Clerk UserButton)
- ASC home dashboard with usage stats and "Start New Prior Auth Case" flow
- Sales rep dashboard with MRR and pipeline tracking

### Compliance Documents
- SECURITY.md — encryption, PHI controls, secret rotation, audit trail
- FDA_POSITIONING.md — non-device CDS exemption analysis
- TRAIGA AI disclosure in all PDF exports

## Database Schema (14 migrations)
- **organizations** (name, is_active, baa_signed_at, stripe_customer_id, subscription_status, subscription_tier, monthly_extraction_count, billing_cycle_start, overage_budget_cap, alert_at_80_sent, alert_at_100_sent, is_admin, verticals)
- **api_keys** (organization_id, key_hash SHA-256, name, is_active)
- **ingestion_jobs** (tenant_id, source_type, status, file_key, original_filename, file_size_bytes, metadata_json, error_message)
- **extraction_results** (tenant_id, diagnosis_code, treatments, implant, robotic, justification, confidence, outcome, raw_extraction_json, schema_version)
- **payer_narratives** (tenant_id, narrative_text, model_used, prompt_version, payer, procedure)
- **payer_policies** (payer, procedure, criteria JSONB, source_url, source_hash, version, effective_date, verified_date, changelog, status)
- **payer_policy_documents** (payer, procedure, title, source_url, source_hash, status, total_chunks, metadata_json)
- **payer_policy_chunks** (document_id, policy_id, payer, procedure, section_title, content, embedding VECTOR(384), page_number, chunk_index, char_start, char_end)
- **narrative_citations** (narrative_id, marker, claim_text, source_type, source_chunk_id, source_text, page_number, section_title)
- **kg_nodes** (node_type, label, properties JSONB) — unique on (node_type, label)
- **kg_edges** (source_node_id, target_node_id, edge_type, properties JSONB, confidence, source_chunk_id)
- **clinical_note_embeddings** (tenant_id, chunk_index, content, embedding VECTOR(1536)) — schema ready, Phase 2
- **audit_log** (tenant_id, action, resource_type, resource_id, request_id, ip_address, metadata_json)

## Post-Deploy Setup

After deploying, run these admin endpoints once to seed the intelligence layer:
1. `POST /api/v1/policy-docs/seed-chunks` — generates 180 policy chunks from 30 existing policies
2. `POST /api/v1/graph/build` — builds knowledge graph (~60 nodes, ~120 edges)

## Architecture: Payer Intelligence Pipeline

```
Clinical Note → PHI Scrub → LLM Extraction → ExtractionResult
                                                    │
                                    User selects payer + procedure
                                                    │
                                    ┌───────────────┼───────────────┐
                                    ▼               ▼               ▼
                              Policy Chunks    Payer Criteria   Knowledge Graph
                              (RAG context)    (requirements)   (cross-payer insights)
                                    │               │               │
                                    ▼               ▼               │
                              Cited Narrative Prompt (v3.0)         │
                                    │                               │
                                    ▼                               │
                              Claude Sonnet → Narrative + Citations  │
                                    │                               │
                                    ▼                               ▼
                              NarrativePanel              Readiness Score
                              (inline [N] markers,        (payer-specific gaps,
                               hover tooltips,             submission portal,
                               Sources panel)              cross-payer intel)
```

## Roadmap: Known Gaps for Full Beta

### Product Gaps (require design decisions)
- **Multi-document case assembly** — no concept of a "case" grouping multiple documents (DICOM + clinical note + robotic report)
- **Narrative editing in-app** — users can't edit narrative text before export
- **Appeal letter generation** — denied outcomes have no workflow
- **Email notifications** — no alerts when jobs complete/fail/hit budget cap
- **Batch upload** — one file at a time, no queue
- **SSO / team accounts** — one API key per org, no individual users
- **CPT code support** — prior auths need CPT codes alongside ICD-10

### Technical Debt
- **N+1 query** in admin list_organizations (separate COUNT per org)
- **No LLM mock tests** — test suite depends on real API if key configured
- **No Stripe webhook tests** — webhook handler uncovered
- **SSE reconnection** — no retry on network error
- **Missing composite index** — (tenant_id, created_at) for analytics queries at scale

### Phase 2: Payer Intelligence Evolution
- **Semantic search** — add embeddings to policy chunks (VECTOR(384) column ready)
- **Policy document auto-update** — scheduled URL re-fetch with source_hash change detection
- **Knowledge graph expansion** — promote from experimental to primary intelligence layer; add cross-procedure relationships, appeal precedent tracking, denial pattern recognition
- **PDF policy viewer** — render source PDFs with citation highlight overlays
- **Fax integration** — "fax to payer" from the narrative panel

## Core Rules

1. **Check before filing:** Most features below are already built. Check this spec before creating issues.
2. **No new vendors:** Anthropic only for LLM. Clerk for auth. Stripe for billing. No exceptions without founder approval.
3. **No architecture changes:** Multi-tenancy, ScrubbedText type guard, server-side proxy, and JSONB extraction storage are locked decisions.
4. **Atomic issues:** One PR per issue. If it touches >5 files, break it up.
5. **Docs go in /docs:** Don't modify code files. Strategic documents go in the /docs directory.
6. **Priority labels required:** P0 > P1 > P2. Claude Code works highest priority first.
7. **Tenant isolation is non-negotiable:** Every data-access endpoint MUST verify tenant_id ownership. Return 404 (not 403) to avoid leaking record existence.
8. **Error messages must be sanitized:** Never expose internal paths, stack traces, or infrastructure details to users.
9. **Audit logs must include tenant_id:** All audit events must be traceable to a specific tenant for HIPAA compliance.
