# DocPilot

[![CI](https://github.com/arjun-kanniah/docpilot/actions/workflows/ci.yml/badge.svg)](https://github.com/arjun-kanniah/docpilot/actions/workflows/ci.yml)

**Ask questions about your documents and get answers with citations.** Upload PDFs and
Markdown, and DocPilot retrieves the relevant passages and answers with sources you can check.
The LLM provider is switchable per request.

> **Status:** early development. Ingestion, semantic search and streamed answers with citations
> work today. See the [roadmap](#roadmap).

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

To try it without your own files, upload [`demo/aurora_knowledge_base.pdf`](demo/), a fictional
company knowledge base, and ask the questions in
[`demo/sample_questions.md`](demo/sample_questions.md).

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
| `GET /api/models` | Configured LLM providers, their allowed models, and the default |
| `POST /api/ask` | Stream an answer with citations (Server-Sent Events) |

## How answering works

1. **Retrieve** the passages closest to the question (6 by default).
2. **Prompt** the chosen model with the passages numbered as sources. It must cite each claim
   as `[n]`, say so when the sources don't hold the answer, and ignore any instructions found
   inside documents.
3. **Stream** the answer back as Server-Sent Events: `sources` first (so the UI can show them
   right away), then `delta` text chunks, then `done` with the model and token usage, or `error`.

Validation and retrieval happen before the stream opens, so a bad request gets a normal 4xx.

The web app renders answers as Markdown (including tables) with citations as links to their
sources. Because answers are shaped by uploaded documents, raw HTML is dropped and images are
never loaded, so a malicious document can't inject script or leak data through an image URL.

### Choosing a model

Providers are enabled by their API keys in `.env` (`ANTHROPIC_API_KEY`, `GEMINI_API_KEY`).
The default is `DOCPILOT_LLM_PROVIDER` / `DOCPILOT_LLM_MODEL`, and a request (or the picker
in the UI) can choose any allowlisted model:

| Provider | Models (first is the default) |
|---|---|
| Claude | `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5` |
| Gemini | `gemini-3.8-flash`, `gemini-3.5-flash-lite` |

The allowlist lives in [`backend/src/docpilot/llm/providers.py`](backend/src/docpilot/llm/providers.py).
Each provider wraps its official SDK behind one small streaming interface
([`llm/base.py`](backend/src/docpilot/llm/base.py)), so adding one is a single file.

Interactive API docs are at http://localhost:8000/docs while `just dev-api` is running.

## Evaluation

[`demo/`](demo/) holds a fictional company knowledge base and 21 questions with reference
answers, including two the document can't answer. `just eval` runs them through the same
prompt and streaming path as the app, and `claude-opus-5-5` grades each answer against its
reference with a structured verdict. Retrieval and citations are scored in code.

| Answering model | Correct | Declined when it should | Cites the right page | Cost per question |
|---|---|---|---|---|
| Claude Opus 5.5 | 19/19 | 2/2 | 100% | ~$0.013 |
| Claude Haiku 5.5 | 19/19 | 2/2 | 100% | ~$0.0003 |
| Gemini 3.5 Flash-Lite | 19/19 | 2/2 | 100% | free tier |

Retrieval finds the right page for every question (mean reciprocal rank 0.97), and CI fails if
that drops below 90%. The grader is checked first: it passes the reference answers and fails
"I don't know". This small set is a regression check rather than a benchmark. See
[the results and their caveats](demo/eval-results/).

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
- [x] Q&A: retrieve passages, stream answers with citations
- [x] Provider switch: Claude ⇄ Gemini behind one interface, per request
- [ ] OpenAI provider
- [x] Evaluation: a question set with graded answers; retrieval checked in CI
- [ ] Deploy: Cloud Run + Cloud SQL via Terraform, with spend guardrails
- [ ] Agent mode: multi-step research across documents

## License

[MIT](LICENSE)
