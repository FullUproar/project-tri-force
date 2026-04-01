# CortaLoom

**AI-powered clinical data extraction and prior authorization for orthopaedic ASCs.**

CortaLoom normalizes fragmented clinical data — robotic surgical outputs, DICOM imaging, and EHR notes — into structured prior authorization submissions. Upload a document, get a payer-ready narrative in seconds.

## Architecture

```
Frontend (Next.js) → FastAPI Backend → Claude Sonnet (LLM)
                          ↓
                   PostgreSQL (Neon) + MinIO (S3)
```

- **Frontend**: Next.js 15, React 19, Tailwind, TanStack Query
- **Backend**: FastAPI, SQLAlchemy 2.0 (async), Alembic
- **Database**: Neon PostgreSQL + pgvector
- **AI**: LangChain + Anthropic Claude (structured extraction + narrative generation)
- **Storage**: MinIO (dev) / S3 (production)
- **PHI Scrubbing**: Regex + Microsoft Presidio (dual-pass)

## Quick Start

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate  # or .venv/Scripts/activate on Windows
pip install -e ".[dev]"
cp .env.example .env       # add your Anthropic API key
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

**With Docker** (MinIO for local file storage):
```bash
docker compose up minio minio-init -d
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/ingest/dicom` | Upload DICOM, extract metadata, strip PHI |
| POST | `/api/v1/ingest/clinical-note` | Upload clinical note text |
| POST | `/api/v1/ingest/robotic-report` | Upload robotic report PDF |
| GET | `/api/v1/ingest/jobs` | List all jobs |
| GET | `/api/v1/ingest/jobs/{id}` | Get job status + extraction results |
| GET | `/api/v1/ingest/jobs/{id}/status` | SSE real-time processing updates |
| POST | `/api/v1/ingest/jobs/{id}/retry` | Retry a failed job |
| POST | `/api/v1/extraction/{id}/narrative` | Generate payer narrative |
| GET | `/health` | Health check with DB status |

All `/api/v1` endpoints require `X-API-Key` header.

## Testing

```bash
cd backend
pytest -v  # 43 tests
```

## Environment Variables

### Backend (`backend/.env`)
- `TF_DATABASE_URL` — PostgreSQL connection string
- `TF_ANTHROPIC_API_KEY` — Anthropic API key
- `TF_API_KEY` — API authentication key
- `TF_MINIO_ENDPOINT` — MinIO/S3 endpoint
- `TF_MINIO_ACCESS_KEY` / `TF_MINIO_SECRET_KEY` — Storage credentials

### Frontend (`frontend/.env.local`)
- `NEXT_PUBLIC_API_URL` — Backend URL (default: http://localhost:8000)
- `NEXT_PUBLIC_API_KEY` — API key matching backend
