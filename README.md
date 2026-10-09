# DocPilot

[![CI](https://github.com/arjun-kanniah/docpilot/actions/workflows/ci.yml/badge.svg)](https://github.com/arjun-kanniah/docpilot/actions/workflows/ci.yml)

**Ask questions about your documents and get answers with citations.** Upload PDFs and
Markdown, and DocPilot retrieves the relevant passages and answers with sources you can check.
The LLM provider is switchable per request.

> **Status:** early development. The project skeleton, toolchain and CI are in place; the
> features below are being built in the order listed in the [roadmap](#roadmap).

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
just db               # start Postgres + pgvector in Docker
just dev-api          # terminal 1: API on http://localhost:8000
just dev-web          # terminal 2: web app on http://localhost:5173
```

Run `just` to see every task, and `just check` to run what CI runs.

## Project layout

```
backend/    FastAPI service (src/docpilot, tests)
frontend/   React + TypeScript web app
.devcontainer/  reproducible dev environment
justfile    task runner: setup, dev, lint, test
mise.toml   pinned toolchain
```

## Roadmap

- [x] Skeleton: API + web app, dev container, CI
- [ ] Ingestion: upload PDF/Markdown → chunk → embed → store in pgvector
- [ ] Q&A: retrieve passages, stream answers with citations
- [ ] Provider switch: Claude ⇄ Gemini (OpenAI next) behind one interface
- [ ] Evaluation: a question set with scored answers, run in CI
- [ ] Deploy: Cloud Run + Cloud SQL via Terraform, with spend guardrails
- [ ] Agent mode: multi-step research across documents

## License

[MIT](LICENSE)
