# DocPilot

[![CI](https://github.com/arjun-kanniah/docpilot/actions/workflows/ci.yml/badge.svg)](https://github.com/arjun-kanniah/docpilot/actions/workflows/ci.yml)

**Ask questions about your documents and get answers with citations.** Upload PDFs and
Markdown, and DocPilot retrieves the relevant passages and answers with sources you can check.
The LLM provider is switchable per request.

> **Status:** early development. Document ingestion and semantic search work today; answers
> with citations are next. See the [roadmap](#roadmap).

## Stack

| Layer | Choice |
|---|---|
| API | Python 3.12, FastAPI, managed with [uv](https://docs.astral.sh/uv/) |
| Web | React 19 + TypeScript, Vite |
| Search | PostgreSQL + [pgvector](https://github.com/pgvector/pgvector) |
| LLMs | Claude and Gemini behind one provider interface; OpenAI planned |
| Tooling | [mise](https://mise.jdx.dev) (toolchain), [just](https://just.systems) (tasks), dev container, GitHub Actions |
| Cloud | Google Cloud Run + Cloud SQL, provisioned with Terraform (planned) |

## Quick start

**Option A: dev container (nothing to install but Docker + VS Code).** Open the folder in
VS Code and choose *Reopen in Container*. Tools and dependencies install automatically.

**Option B: local.**

```bash
mise install          # node, uv, just at pinned versions
cp .env.example .env  # add API keys when needed
just setup            # install backend + frontend dependencies
just migrate          # start Postgres + pgvector in Docker and create the schema
just dev-api          # terminal 1: API on http://localhost:8000
just dev-web          # terminal 2: web app on http://localhost:5173
```

Run `just` to see every task, and `just check` to run what CI runs.

## How ingestion works

1. **Upload** a PDF, Markdown or text file (up to 20 MB). Re-uploading identical bytes is detected
   by SHA-256 and skipped.
2. **Extract** text per page (PDFs keep page numbers for citations).
3. **Chunk** into ~1,000-character passages on paragraph and sentence boundaries, with a
   150-character overlap so a sentence cut at a boundary is still findable.
4. **Embed** each chunk locally with `BAAI/bge-small-en-v1.5` (384 dimensions, CPU, no API cost).
5. **Store** in Postgres with an HNSW index for fast cosine-similarity search.

| Endpoint | Purpose |
|---|---|
| `POST /api/documents` | Upload and index a file |
| `GET /api/documents` | List documents with page and chunk counts |
| `DELETE /api/documents/{id}` | Remove a document and its chunks |
| `POST /api/search` | Top-k passages for a query, with similarity scores |

Interactive API docs are at http://localhost:8000/docs while `just dev-api` is running.

## Project layout

```
backend/    FastAPI service (src/docpilot), Alembic migrations, tests
frontend/   React + TypeScript web app
.devcontainer/  reproducible dev environment
justfile    task runner: setup, dev, lint, test
mise.toml   pinned toolchain
```

## Roadmap

- [x] Skeleton: API + web app, dev container, CI
- [x] Ingestion: upload PDF/Markdown/text → chunk → embed locally → store in pgvector
- [x] Semantic search over chunks, with page references
- [ ] Q&A: retrieve passages, stream answers with citations
- [ ] Provider switch: Claude ⇄ Gemini (OpenAI next) behind one interface
- [ ] Evaluation: a question set with scored answers, run in CI
- [ ] Deploy: Cloud Run + Cloud SQL via Terraform, with spend guardrails
- [ ] Agent mode: multi-step research across documents

## License

[MIT](LICENSE)
