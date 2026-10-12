# DocPilot

[![CI](https://github.com/arjun-kanniah/docpilot/actions/workflows/ci.yml/badge.svg)](https://github.com/arjun-kanniah/docpilot/actions/workflows/ci.yml)

**Ask questions about your documents and get answers with citations.** Upload PDFs and
Markdown, and DocPilot retrieves the relevant passages and answers with sources you can check.
The LLM provider is switchable per request.

**[Try the live demo](https://docpilot.arjunkanniah.dev)**: ask about a fictional
company's knowledge base (read-only, cheap models, rate-limited). See [Deploying](#deploying)
for how it runs.

![DocPilot answering a question with a cited comparison table](docs/demo.gif)

<sub>Recorded on the live demo with Claude Haiku; the wait for the model's first token is shortened.</sub>

## Stack

| Layer | Choice |
|---|---|
| API | Python 3.12, FastAPI, managed with [uv](https://docs.astral.sh/uv/) |
| Web | React 19 + TypeScript, Vite |
| Search | PostgreSQL + [pgvector](https://github.com/pgvector/pgvector) |
| LLMs | Claude, OpenAI and Gemini behind one provider interface |
| Tooling | [mise](https://mise.jdx.dev) (toolchain), [just](https://just.systems) (tasks), dev container, GitHub Actions |
| Cloud | Google Cloud Run, Neon serverless Postgres, Cloudflare (DNS + Worker), Terraform, deploys from GitHub Actions |

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

Providers are enabled by their API keys in `.env` (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`,
`GEMINI_API_KEY`).
The default is `DOCPILOT_LLM_PROVIDER` / `DOCPILOT_LLM_MODEL`, and a request (or the picker
in the UI) can choose any allowlisted model:

| Provider | Models (first is the default) |
|---|---|
| Claude | `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5` |
| OpenAI | `gpt-6.1-sol`, `gpt-6-luna`, `gpt-6-astra` |
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
| GPT-6.1 Sol | 19/19 | 2/2 | 100% | ~$0.003 |
| GPT-6 Luna | 19/19 | 2/2 | 100% | ~$0.0002 |
| Gemini 3.5 Flash-Lite | 19/19 | 2/2 | 100% | free tier |

Retrieval finds the right page for every question (mean reciprocal rank 1.00), and CI fails if
that drops below 90%. The grader is checked first: it passes the reference answers and fails
"I don't know". This small set is a regression check rather than a benchmark. See
[the results and their caveats](demo/eval-results/).

## Deploying

The public demo runs on Google Cloud Run with a [Neon](https://neon.tech) Postgres database,
behind a Cloudflare Worker that serves the custom domain. All three have free tiers and the
first two scale to zero, so an idle demo costs nothing.

```mermaid
flowchart LR
    U[Browser] --> W["Cloudflare Worker<br/>docpilot.arjunkanniah.dev"] --> R["Cloud Run<br/>API + web app + embedding model"]
    R --> N[("Neon Postgres<br/>+ pgvector")]
    R --> L["Claude · OpenAI · Gemini"]
    S[Secret Manager] -. keys and database URL .-> R
    G[GitHub Actions] -- "Workload Identity Federation<br/>(no key files)" --> A[Artifact Registry] --> R
```

- **One container** serves the API and the built web app, with the embedding model baked in so
  cold starts never download it ([`Dockerfile`](Dockerfile)).
- **Every push to `main`** that passes CI builds the image, runs a migration job (which also
  loads the demo PDF), deploys a new revision and smoke-tests it.
- **[`infra/`](infra/)** (Terraform) owns the service, the migration job, least-privilege service
  accounts, GitHub's deploy access (limited to this repo's `main` branch), a budget alert, and
  the Cloudflare side: DNS, the Worker and redirects. Provider keys, the database URL and the
  Cloudflare token are stored with `just secret`, so they never reach code or Terraform state.
- **Why a Worker for the domain:** Cloud Run's built-in domain mapping isn't offered in
  us-east5, a Google load balancer costs about USD 18 a month, and Firebase Hosting buffers
  responses, which would break streamed answers. The Worker streams them through
  ([`infra/worker/proxy.js`](infra/worker/proxy.js)) and passes on the visitor's IP for the rate
  limit, with a shared secret so direct callers can't forge it.

**Demo mode** (`DOCPILOT_DEMO_MODE=true`) guards the public URL: the document library is
read-only, only cheap models are offered, each visitor gets 20 questions an hour, and
instances are capped at two. The demo's API keys also have spend limits set at each provider.

One-time setup, using a dedicated gcloud profile named `docpilot`:

```bash
just infra-bootstrap                 # APIs, Terraform state bucket, terraform init
just secret database-url             # Neon connection string; likewise anthropic-api-key,
                                     # openai-api-key, gemini-api-key, cloudflare-api-token
cp infra/terraform.tfvars.example infra/terraform.tfvars   # then fill it in
just infra apply                     # everything else (the domains must already be
                                     # active zones in Cloudflare)
```

Then set the repository variables `GCP_PROJECT_ID`, `GCP_REGION`, `GCP_WIF_PROVIDER` and
`GCP_DEPLOY_SA` from `just infra output`, and the next push to `main` deploys.

## Project layout

```
backend/        FastAPI service (src/docpilot), Alembic migrations, tests
frontend/       React + TypeScript web app
demo/           fictional knowledge base, evaluation set and results
infra/          Terraform for Google Cloud and Cloudflare, and the Worker
Dockerfile      production image (API + web app + embedding model)
.devcontainer/  reproducible dev environment
justfile        task runner: setup, dev, lint, test, eval, infra
mise.toml       pinned toolchain
```

## Roadmap

- [x] Skeleton: API + web app, dev container, CI
- [x] Ingestion: upload PDF/Markdown/text → chunk → embed locally → store in pgvector
- [x] Semantic search over chunks, with page references
- [x] Q&A: retrieve passages, stream answers with citations
- [x] Provider switch: Claude, OpenAI and Gemini behind one interface, per request
- [x] Evaluation: a question set with graded answers; retrieval checked in CI
- [x] Deploy: Cloud Run + Neon via Terraform, deployed from CI, with spend guardrails
- [x] Custom domain through a Cloudflare Worker, keeping answers streamed
- [ ] Agent mode: multi-step research across documents

## License

[MIT](LICENSE)
