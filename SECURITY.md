# CortaLoom Security & HIPAA Compliance

## Overview

CortaLoom processes clinical data for orthopaedic prior authorization. This document describes the security controls in place to protect clinical data in accordance with HIPAA technical safeguards.

## Encryption

### In Transit (All connections TLS-encrypted)

| Connection | Protocol | Verification |
|---|---|---|
| Browser → Frontend (Vercel) | HTTPS | Vercel enforces TLS with auto-provisioned certs |
| Browser → Backend API (Railway) | HTTPS | Railway provides TLS termination |
| Backend → PostgreSQL (Neon) | PostgreSQL + TLS | `?ssl=require` in connection string |
| Backend → Object Storage (Cloudflare R2) | HTTPS | boto3 with `use_ssl=True` |
| Backend → Anthropic API | HTTPS | SDK default, pinned to api.anthropic.com |

HSTS header (`Strict-Transport-Security: max-age=31536000`) is set on all API responses.

### At Rest

| Storage | Encryption | Provider |
|---|---|---|
| PostgreSQL (Neon) | AES-256 | Neon encrypts all data at rest by default |
| Object Storage (Cloudflare R2) | AES-256 | R2 encrypts all objects at rest by default |
| Vercel (frontend assets) | N/A | Static assets only, no clinical data |

## PHI Protection

### De-identification Pipeline

All clinical text passes through a dual-pass PHI scrubber before reaching any LLM API:

1. **Regex pass** — Deterministic pattern matching for SSN, MRN, phone, email, dates
2. **Presidio NER pass** — Microsoft Presidio with `en_core_web_lg` spaCy model for person names, locations, medical license numbers

The scrubber returns a `ScrubbedText` NewType. LLM service functions only accept this type, enforced at the code level.

### DICOM De-identification

DICOM files are de-identified using the Safe Harbor method:
- All `PersonName` (PN) VR tags are removed
- Explicit PHI tags removed: PatientName, PatientID, PatientBirthDate, InstitutionName, ReferringPhysicianName, and 20+ additional tags per DICOM Supplement 142
- De-identified file is stored; original is never persisted

### LLM API Usage

- **Provider**: Anthropic (Claude Sonnet)
- **Zero retention**: Anthropic API customers are opted out of training data by default
- **No PHI in prompts**: All text is scrubbed before LLM calls
- **No PHI in logs**: Log entries contain job IDs, counts, and status only — never clinical text content

## Authentication & Access Control

- API key authentication required on all `/api/v1` endpoints via `X-API-Key` header
- `/health` endpoint is unauthenticated (returns no clinical data)
- SSE endpoints accept API key via query parameter (EventSource limitation)
- API key stored as `SecretStr` in config — never logged or exposed in error messages

## Security Headers

All API responses include:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`

## Audit Trail

- All ingestion jobs are tracked in `ingestion_jobs` table with timestamps
- All extraction results stored with the LLM model and prompt version used
- All narratives stored with generation metadata
- Structured JSON logging with request ID correlation across the pipeline

## Data Flow Audit

```
Upload → File stored in R2 (DICOM: de-identified first)
       → Raw text extracted (pydicom/pypdf)
       → PHI scrubber (regex + Presidio) → ScrubbedText
       → Claude API (scrubbed text only)
       → Extraction results stored in PostgreSQL
       → Narrative generated from extraction (no raw text)
```

At no point does raw (pre-scrub) clinical text enter the database. The only raw text storage is the uploaded file in R2 (clinical notes as .txt). DICOM files are de-identified before R2 storage.

**Known gap**: Clinical note .txt files stored in R2 contain the original uploaded text (pre-scrub). This is intentional for retry functionality — the scrubber runs on re-download. R2 encryption at rest protects these files. Phase 2 will add the option to store only scrubbed versions.

## Encryption Key Management

### Data at Rest

| Storage | Encryption | Key Owner | Key Rotation |
|---|---|---|---|
| Neon PostgreSQL | AES-256 | Neon (managed) | Automatic, transparent to application |
| Cloudflare R2 | AES-256 | Cloudflare (managed) | Automatic, transparent to application |

CortaLoom does **not** manage encryption keys directly. Both Neon and Cloudflare R2 use provider-managed encryption where the cloud provider handles key generation, rotation, and storage in hardware security modules (HSMs).

**Decision**: Provider-managed encryption is appropriate for Phase 1. Customer-managed keys (BYOK) using AWS KMS or Cloudflare KMS can be added in Phase 2 if enterprise customers or BAA terms require it.

### Data in Transit

All connections use TLS 1.2+ with certificates managed by the respective providers (Vercel, Railway, Neon, Cloudflare). No application-level certificate management is required.

### Application-Level Encryption

The `raw_extraction_json` field in `extraction_results` stores the full LLM output. This field is protected by:
1. Database encryption at rest (Neon AES-256)
2. PHI scrubbing before LLM processing (no raw PHI should reach this field)
3. Tenant isolation (queries scoped by tenant_id)

**Decision**: Application-level field encryption (e.g., pgcrypto) is not implemented in Phase 1. The risk is mitigated by the PHI scrubber running before any data reaches the LLM or database. If a BAA audit requires field-level encryption, add pgcrypto with a per-tenant encryption key stored in a secrets manager.

## Secret Management

| Secret | Storage | Rotation Procedure |
|---|---|---|
| `TF_ANTHROPIC_API_KEY` | Railway env var | 1. Generate new key in Anthropic Console. 2. Update Railway. 3. Wait for redeploy. 4. Revoke old key. |
| `TF_API_KEY` | Railway env var | 1. Update Railway. 2. Update Vercel `API_KEY`. 3. Redeploy both. Legacy key works until Railway redeploys. |
| `TF_DATABASE_URL` | Railway env var | 1. Rotate password in Neon Console. 2. Update Railway. 3. Wait for redeploy. |
| R2 credentials | Railway env var | 1. Create new R2 API token in Cloudflare. 2. Update Railway. 3. Wait for redeploy. 4. Delete old token. |
| `CLERK_SECRET_KEY` | Railway + Vercel env vars | 1. Rotate in Clerk Dashboard. 2. Update both Railway and Vercel. 3. Redeploy both. |
| DB-backed API keys | `api_keys` table (SHA-256 hashed) | 1. Generate new key. 2. Hash and insert into `api_keys`. 3. Give raw key to customer. 4. Deactivate old key (`is_active = false`). |

### Rotation Schedule

- **API keys**: Rotate on customer request or suspected compromise
- **Anthropic key**: Rotate quarterly or on compromise
- **Database credentials**: Rotate quarterly
- **R2 credentials**: Rotate quarterly
- **Clerk keys**: Rotate on Clerk's recommendation or annually

## Reporting Security Issues

## Legal Entity

CortaLoom AI, Inc. — Indiana C Corporation

## Reporting Security Issues

If you discover a security vulnerability, please email security@cortaloom.ai (or contact the founder directly). Do not open a public GitHub issue for security vulnerabilities.
