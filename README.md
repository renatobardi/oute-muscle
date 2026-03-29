# Oute Muscle

**Incident-based code guardrails platform** — turns post-mortems into detection rules so production incidents never repeat.

[![CI](https://github.com/renatobardi/oute-muscle/actions/workflows/ci.yml/badge.svg)](https://github.com/renatobardi/oute-muscle/actions/workflows/ci.yml)
[![Deploy](https://github.com/renatobardi/oute-muscle/actions/workflows/deploy.yml/badge.svg)](https://github.com/renatobardi/oute-muscle/actions/workflows/deploy.yml)

---

## What it does

Every production incident has a root cause that could have been caught in code review. Oute Muscle bridges the gap between post-mortem documentation and the development workflow:

1. **You document an incident** — paste the post-mortem, describe what went wrong
2. **Oute synthesizes a rule** — Semgrep rule generated, reviewed, and merged
3. **The rule ships to CI** — every future PR is scanned; the same mistake is blocked

Three detection layers work together:

| Layer | Type | Behavior |
|-------|------|----------|
| L1 — Semgrep rules | Static analysis | **Blocking** — fails CI before merge |
| L2 — RAG advisory | Semantic similarity | **Advisory** — flags code similar to past incidents |
| L3 — Auto-synthesis | LLM-generated rules | **Progressive** — proposes new rules from uncovered patterns |

## Quick start

### Prerequisites

- Python 3.12+, Node 20+
- [uv](https://github.com/astral-sh/uv) — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Docker (for local DB)
- PostgreSQL 16 with pgvector (or use Docker Compose)

### Setup

```bash
git clone https://github.com/renatobardi/oute-muscle.git
cd oute-muscle

# Install all dependencies (Python + Node)
bash scripts/dev-setup.sh

# Or manually:
uv sync --all-packages --group dev
cd apps/web && npm install && cd ..
```

### Run locally

```bash
# Start the API (FastAPI on :8000)
make dev

# Start the dashboard (SvelteKit on :5173)
make dev-web

# Health check
curl http://localhost:8000/health
```

### Run tests

```bash
make test          # all backend tests
make test-unit     # unit tests only
make test-cov      # with coverage (min 80%)
make test-rules    # Semgrep rule tests
make test-web      # frontend tests
```

## Project structure

```
apps/
  api/              FastAPI backend (Python 3.12)
  web/              SvelteKit dashboard (TypeScript)
  mcp/              MCP Server (Streamable HTTP + OAuth 2.1)
packages/
  core/             Shared domain logic — hexagonal architecture
  db/               SQLAlchemy models + Alembic migrations
  semgrep-rules/    10 rule categories, one YAML per incident pattern
infra/
  gcp/              Terraform — Cloud Run, Cloud SQL, Vertex AI, IAM
scripts/
  dev-setup.sh      First-time setup
  deploy-bootstrap.sh  One-shot GCP environment bootstrap
specs/              SpecKit feature design artifacts
docs/               Architecture, deployment, contributing guides
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check |
| GET | `/health/ready` | Readiness check (DB + LLM) |
| POST | `/v1/waitlist` | Beta waitlist signup |
| GET/POST | `/v1/incidents` | Incident CRUD |
| POST | `/v1/scans` | Trigger code scan |
| GET | `/v1/findings` | Scan findings |
| POST | `/v1/webhooks/github` | GitHub webhook receiver |

Full API docs available at `/docs` (Swagger UI) when running locally.

## Semgrep rule categories

Rules are organized by incident type under `packages/semgrep-rules/`:

- `unsafe-regex` — catastrophic backtracking, unbounded patterns
- `injection` — SQL, command, template injection
- `race-condition` — TOCTOU, shared state without locks
- `missing-error-handling` — unchecked errors, swallowed exceptions
- `resource-exhaustion` — unbounded loops, missing limits
- `missing-safety-check` — absent guards, unchecked inputs
- `deployment-error` — deploy-time footguns
- `data-consistency` — missing transactions, partial updates
- `unsafe-api-usage` — deprecated or dangerous API calls
- `cascading-failure` — missing circuit breakers, retry storms

Rule ID format: `{category}-{NNN}` (e.g., `unsafe-regex-001`). Every rule requires a corresponding test file.

## Tech stack

| Concern | Technology |
|---------|-----------|
| API | FastAPI, asyncpg, Pydantic v2, uvicorn |
| Frontend | SvelteKit, TypeScript strict, Tailwind CSS |
| Database | PostgreSQL 16 + pgvector (HNSW indexes, RLS) |
| LLM | Vertex AI (Gemini 2.5 Flash/Pro) + Claude Sonnet 4 |
| Static analysis | Semgrep (custom rules) |
| Infrastructure | GCP: Cloud Run, Cloud SQL, Vertex AI, Secret Manager |
| CI/CD | GitHub Actions + Workload Identity Federation |
| Monorepo | UV workspaces (Python), npm (frontend) |

## Deployment

Single environment on GCP — **prod** on Cloud Run. Trunk-Based CD.

- Every PR merged to `main` deploys to prod automatically
- No staging, no tags, no manual steps

```bash
# Bootstrap prod infrastructure (one-time)
bash scripts/deploy-bootstrap.sh
```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the full runbook.

## Contributing

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md). Key rules:

- Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`)
- TDD mandatory — no untested code merged
- Every Semgrep rule requires a test file
- 80% coverage gate enforced in CI
- `mypy --strict` on `packages/core/`

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full system design, hexagonal boundaries, and data flow.

## License

Private — all rights reserved. © 2026 Oute.
