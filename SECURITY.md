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

## Secret Management

| Secret | Storage | Rotation |
|---|---|---|
| `TF_ANTHROPIC_API_KEY` | Railway environment variable | Rotate in Anthropic Console + Railway |
| `TF_API_KEY` | Railway environment variable | Update in Railway + Vercel simultaneously |
| `TF_DATABASE_URL` | Railway environment variable | Rotate in Neon Console + Railway |
| R2 credentials | Railway environment variable | Rotate in Cloudflare R2 + Railway |

## Reporting Security Issues

If you discover a security vulnerability, please email security@cortaloom.ai (or contact the founder directly). Do not open a public GitHub issue for security vulnerabilities.
