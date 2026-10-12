# DocPilot task runner. Run `just` to list recipes.

set dotenv-load

_default:
    @just --list

# Install backend and frontend dependencies
setup:
    cd backend && uv sync
    cd frontend && npm ci

# Start the local Postgres + pgvector database
db:
    docker compose up -d --wait db

# Apply database migrations to the dev database
migrate: db
    cd backend && uv run alembic upgrade head

# Stop local services (data is kept in a Docker volume)
down:
    docker compose down

# Run the API with auto-reload on :8000
dev-api:
    cd backend && uv run uvicorn docpilot.main:app --reload --port 8000

# Run the web app on :5173 (proxies /api to :8000)
dev-web:
    cd frontend && npm run dev

# Lint and format-check everything
lint:
    cd backend && uv run ruff check . && uv run ruff format --check .
    cd frontend && npm run lint

# Auto-fix formatting and lint issues where possible
fmt:
    cd backend && uv run ruff check --fix . && uv run ruff format .

# Run tests (backend against a separate docpilot_test database), then the frontend tests and build
test: db
    cd backend && uv run pytest
    cd frontend && npm test && npm run build

# Score retrieval on the demo eval set (free: local embeddings, no API keys)
eval-retrieval: db
    cd backend && uv run python -m docpilot.evaluation retrieval --min-hit-rate 0.9

# Answer and grade the demo eval set (paid API calls). e.g. just eval --model claude-haiku-5-5
eval *args: db
    cd backend && uv run python -m docpilot.evaluation answers {{args}}

# Everything CI runs
check: lint test eval-retrieval
