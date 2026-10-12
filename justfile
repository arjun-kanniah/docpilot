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

# Build the production image locally
image:
    docker build -t docpilot:local .

# --- Google Cloud (always uses the separate "docpilot" gcloud profile) ---

# One-time: enable the APIs Terraform needs, create its state bucket, and init Terraform
infra-bootstrap:
    #!/usr/bin/env bash
    set -euo pipefail
    export CLOUDSDK_ACTIVE_CONFIG_NAME=docpilot
    project=$(gcloud config get-value project 2>/dev/null)
    bucket="${project}-tfstate"
    gcloud services enable serviceusage.googleapis.com cloudresourcemanager.googleapis.com \
        cloudbilling.googleapis.com storage.googleapis.com secretmanager.googleapis.com
    if ! gcloud storage buckets describe "gs://${bucket}" >/dev/null 2>&1; then
        gcloud storage buckets create "gs://${bucket}" --location=us-east4 \
            --uniform-bucket-level-access --public-access-prevention
    fi
    gcloud storage buckets update "gs://${bucket}" --versioning
    cd infra && GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token) \
        terraform init -input=false -backend-config="bucket=${bucket}"

# Store a deployed-app secret from a hidden prompt (database-url, anthropic-api-key, ...)
secret name:
    #!/usr/bin/env bash
    set -euo pipefail
    case "{{name}}" in
        database-url|anthropic-api-key|openai-api-key|gemini-api-key) ;;
        *) echo "Unknown secret '{{name}}'" >&2; exit 1 ;;
    esac
    export CLOUDSDK_ACTIVE_CONFIG_NAME=docpilot
    if ! gcloud secrets describe "{{name}}" >/dev/null 2>&1; then
        gcloud secrets create "{{name}}" --replication-policy=automatic
    fi
    read -rsp "Value for {{name}} (hidden): " value; echo
    [ -n "$value" ] || { echo "Empty value, nothing stored." >&2; exit 1; }
    printf '%s' "$value" | gcloud secrets versions add "{{name}}" --data-file=- >/dev/null
    echo "Stored a new version of {{name}}."

# Run Terraform against the project, e.g. `just infra plan`, `just infra apply`
infra *args:
    #!/usr/bin/env bash
    set -euo pipefail
    export CLOUDSDK_ACTIVE_CONFIG_NAME=docpilot
    export GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token)
    cd infra && terraform {{args}}
