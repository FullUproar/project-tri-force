.PHONY: up down build test lint migrate

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

# Run backend tests
test:
	cd backend && python -m pytest -v

# Run linting
lint:
	cd backend && ruff check . && ruff format --check .
	cd frontend && npm run lint

# Run Alembic migrations
migrate:
	cd backend && alembic upgrade head

# Create a new migration
migration:
	cd backend && alembic revision --autogenerate -m "$(msg)"

# Start backend locally (without Docker)
backend-dev:
	cd backend && uvicorn app.main:app --reload --port 8000

# Start frontend locally (without Docker)
frontend-dev:
	cd frontend && npm run dev
