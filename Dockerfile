# syntax=docker/dockerfile:1
# Production image: the API serves the built web app; the embedding model is baked in so
# cold starts never download it.

# 1. Build the web app
FROM node:24-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# 2. Install the API and download the embedding model
FROM python:3.12-slim-bookworm AS api
COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock backend/README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/src ./src
RUN uv sync --frozen --no-dev --no-editable
ENV DOCPILOT_MODEL_CACHE_DIR=/app/models
RUN .venv/bin/python -c "from docpilot.embeddings import get_embedder; get_embedder().embed_query('warm-up')"

# 3. Runtime: no build tools, non-root
FROM python:3.12-slim-bookworm
RUN useradd --create-home --uid 10001 docpilot
WORKDIR /app
COPY --from=api /app/.venv ./.venv
COPY --from=api --chown=docpilot /app/models ./models
COPY backend/alembic.ini ./
COPY backend/migrations ./migrations
COPY demo/aurora_knowledge_base.pdf ./demo/
COPY --from=web /web/dist ./static
ENV PATH=/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    HF_HUB_OFFLINE=1 \
    DOCPILOT_ENV=production \
    DOCPILOT_MODEL_CACHE_DIR=/app/models \
    DOCPILOT_STATIC_DIR=/app/static
USER docpilot
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn docpilot.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
