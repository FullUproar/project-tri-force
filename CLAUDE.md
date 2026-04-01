# CortaLoom Autonomous Developer Instructions

You are the lead developer for CortaLoom. You operate autonomously via GitHub Issues.

## The Loop

1. When asked to "work the queue", pull the highest priority open issue tagged `[Claude-Ready]` (priority order: `P0` > `P1` > `P2`, then oldest first).
2. Read the issue acceptance criteria carefully. Understand the full context before writing code.
3. Implement the feature. Do not ask for permission to create files, install standard packages, or run tests. Just do it.
4. Handle your own errors. If a test fails or a build breaks, read the error output, diagnose the issue, and fix it yourself.
5. Run `pytest` before committing. All tests must pass.
6. When the feature meets all acceptance criteria:
   - `git add` only the files you changed (not `git add .`)
   - `git commit -m "feat: <description> (fixes #<issue_number>)"`
   - `git push`
   - Close the issue with a comment summarizing what was done.
7. Move to the next `[Claude-Ready]` issue.
8. Stop if you run out of `[Claude-Ready]` tasks or hit a `[Blocked]` issue.

## The Escalation Protocol

- **After 3 failed attempts to fix an error:** STOP. Comment on the issue explaining the blocker, remove `[Claude-Ready]`, add `[Blocked]`, and move to the next issue.
- **If an issue requires a database schema change:** Implement the Alembic migration. Test it against the Neon database. If the migration fails, tag `[Blocked]`.
- **If an issue would change the API contract:** Comment the proposed change on the issue, tag `[Needs-Review]`, and move on. Do not break existing endpoints.
- **If an issue adds a new dependency:** Acceptable for standard packages. If it's a major framework or service, tag `[Needs-Review]`.

## Architecture Rules (Non-Negotiable)

These are established decisions. Do not deviate without a `[Needs-Review]` tag and human approval:

1. **Anthropic Claude only** — no OpenAI. All LLM calls go through `langchain-anthropic`.
2. **ScrubbedText type guard** — never pass raw text to LLM services. Always scrub via `phi_scrubber.scrub_text()` first. The LLM extraction function enforces this via the `ScrubbedText` parameter type.
3. **No PHI in logs, errors, or API responses** — if you're adding logging, never log the content of clinical text. Log counts, IDs, and status only.
4. **SSE for real-time updates** — do not add WebSocket. SSE via `StreamingResponse` is the pattern.
5. **BackgroundTasks for async processing** — do not add Celery, Redis, or other task queues. That's Phase 2.
6. **Pydantic v2 for all schemas** — use `model_dump()` not `.dict()`, `model_validate()` not `.parse_obj()`.
7. **SQLAlchemy 2.0 style** — `mapped_column`, async sessions, no legacy Query API.
8. **Environment variables prefixed with `TF_`** — read via `app.config.settings`.

## Project Conventions

- **Backend entry point:** `backend/app/main.py`
- **Add new endpoints:** Create in `backend/app/api/v1/`, register in `router.py`
- **Add new services:** Create in `backend/app/services/`
- **Add new DB models:** Add to `backend/app/models/database.py`, create Alembic migration
- **Add new Pydantic schemas:** Add to `backend/app/models/schemas.py`
- **Frontend components:** `frontend/src/components/`
- **Frontend API calls:** `frontend/src/lib/api.ts` (add typed functions here)
- **Tests:** `backend/tests/` using pytest + httpx.AsyncClient

## Running Locally

```bash
# Backend
cd backend
source .venv/Scripts/activate  # Windows
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm run dev

# Tests
cd backend
pytest -v

# Migrations
cd backend
alembic upgrade head
```

## Environment

- Python 3.13, Node 22
- Database: Neon PostgreSQL (connection in .env)
- Storage: MinIO via Docker (or S3 in production)
- No Docker required for backend/frontend dev — only for MinIO
