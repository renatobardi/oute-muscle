# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Oute Muscle** is an incident-based code guardrails platform that prevents production incidents from recurring in code. It bridges post-mortem documentation to detection rules via 3 layers: static Semgrep rules (blocking), RAG advisory (consultive), and automatic rule synthesis (progressive).

## Constitution

Ratified at `.specify/memory/constitution.md` (v1.1.0, 12 principles). Key principles:

- **Incident Traceability**: Every rule links to a real documented incident
- **Three-Layer Detection**: L1 Semgrep (blocking) → L2 RAG (consultive) → L3 Synthesis (progressive)
- **Hexagonal Boundaries**: Ports/adapters only at real boundaries (LLM router, delivery channels, GCP adapters) — no speculative interfaces
- **Incremental Complexity**: L1 proven before L2, L2 before L3. Abstractions require 2 implementations
- **Quality Gates**: TDD mandatory, mypy strict, Ruff, ESLint (coverage threshold currently at 40%, target 80%)

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI (Python 3.12+), asyncpg, pydantic v2, uvicorn |
| Frontend | SvelteKit (adapter-node), Svelte 5, TypeScript strict, Tailwind CSS v4, bits-ui |
| Auth | Firebase Auth (client + admin SDK), session cookies (httpOnly, 5-day), shared with oute.me |
| Database | PostgreSQL 16 + pgvector (Cloud SQL), HNSW indexes, RLS |
| LLM | Vertex AI (Gemini 2.5 Flash/Pro + Claude Sonnet 4), text-embedding-005 |
| Static Analysis | Semgrep (custom rules with mandatory test files) |
| Infra | GCP Managed: Cloud Run (`muscle-prod-api`, `muscle-prod-web`), Cloud SQL, Vertex AI, Secret Manager |
| Domain | `muscle.oute.pro` (web + API via BFF), `mcp.muscle.oute.pro` (MCP) |
| CI/CD | GitHub Actions, Workload Identity Federation, Conventional Commits |
| Monorepo | UV workspaces (Python), npm (frontend) |

## Development Commands

All common commands are in the `Makefile`. Run `make help` to see all targets.

### Setup

```bash
scripts/dev-setup.sh     # First-time setup: checks prereqs (uv, node, gcloud), installs deps, pre-commit hooks
make install             # Install all deps: uv sync --all-packages --extra dev + npm install in apps/web
```

### Running

```bash
make dev                 # FastAPI dev server on 0.0.0.0:8000 with reload
make dev-web             # SvelteKit dev server
```

### Testing

```bash
make test                # All backend tests (pytest)
make test-unit           # Unit tests only: apps/api/tests/unit/ + packages/core/tests/
make test-cov            # Tests with coverage (HTML report in htmlcov/, fails under 40%)
make test-rules          # Semgrep rule tests: semgrep --test packages/semgrep-rules/
make test-web            # Frontend unit tests: vitest run
make test-e2e            # Playwright e2e tests

# Run a single Python test:
pytest apps/api/tests/unit/test_foo.py::test_bar -v

# Run a single frontend test:
cd apps/web && npx vitest run src/lib/foo.test.ts

# Skip slow tests:
pytest -m "not integration and not acceptance"
```

Custom markers: `acceptance` (full user-flow), `integration` (requires live DB/network). Coverage omits `tests/` and `migrations/`.

### Linting & Type Checking

```bash
make lint                # Ruff check + ESLint
make type-check          # mypy --strict packages/core/ + svelte-check
make format              # Ruff format + Prettier
```

### Database Migrations

```bash
make migrate-up          # alembic upgrade head
make migrate-down        # alembic downgrade -1
make migrate-gen MSG="description"  # autogenerate new migration
```

Alembic config: `packages/db/alembic.ini`. Migrations live in `packages/db/src/migrations/`.

## Monorepo Structure

```
apps/api/          — FastAPI backend (API + workers)
apps/web/          — SvelteKit dashboard
apps/mcp/          — MCP Server (Streamable HTTP + OAuth 2.1)
packages/core/     — Shared domain logic (hexagonal: domain/, ports/, adapters/)
packages/db/       — SQLAlchemy models + Alembic migrations
packages/semgrep-rules/ — Rules organized by 10 categories
infra/gcp/         — Terraform (Cloud Run, Cloud SQL, Vertex AI, IAM)
scripts/           — CLI tools (dev-setup, deploy-bootstrap, rule sync, seed)
.github/workflows/ — CI (lint, test, semgrep), deploy (Cloud Run)
specs/             — SpecKit feature design artifacts
```

UV workspace members: `apps/api`, `apps/mcp`, `packages/core`, `packages/db`.

## Architecture

### Hexagonal Core (`packages/core/`)

- **`src/domain/`** — Pure business logic, no framework dependencies
- **`src/ports/`** — Interface definitions (Protocol classes for adapters/services)
- **`src/adapters/`** — Only GitHub adapter (PyGithub, no heavy infra deps)

`packages/core` depends only on Pydantic — no GCP, no FastAPI, no SQLAlchemy.

Adapter implementations live where their dependencies are:
- **`packages/db/src/adapters/`** — PostgreSQL adapters (incident repo, vector search, advisory repo, scan repo) — depends on SQLAlchemy + pgvector
- **`apps/api/src/adapters/`** — Vertex AI adapters (embedding, LLM Flash/Pro/Claude) + synthesis repos — depends on google-cloud-aiplatform, anthropic[vertex]

### API Layer (`apps/api/`)

- **Entry point**: `apps/api/src/main.py` — FastAPI app with lifespan, DI container, routes at `/v1`
- **Routes**: `src/routes/` — one router per domain (health, waitlist, incidents, scans, findings, webhooks, synthesis, tenants, audit, admin). `sarif.py` is a utility module (not a router). `admin.py` provides 8 cross-tenant admin endpoints at `/v1/admin/`
- **Middleware**: `src/middleware/` — `rate_limit` and `correlation` are registered as global middleware; `auth` (includes `require_admin` dependency), `webhook_auth`, and `rls` (includes `is_admin` flag for RLS bypass) exist as modules but are used as route-level dependencies/functions, not global middleware. CORS restricted to `muscle.oute.pro`, `oute.pro`, and localhost
- **Workers**: `src/workers/` — background tasks (synthesis, RAG, retention purge, archive)
- **Config**: `src/config.py` — Pydantic BaseSettings (DB URL, JWT key, GCP project, Vertex AI location, ADMIN_EMAILS, ALLOWED_ORIGINS)
- **Services**: `src/services/` — application services (false_positive.py for FR-028 auto-disable)

### Dependency Injection

Two-tier DI pattern:
- **App-level singletons** in `DIContainer` (`apps/api/src/main.py`): session factory, embedding adapter, LLM adapters (Gemini Flash/Pro, Claude Sonnet). Uses `NullLLMAdapter` when GCP is not configured (local dev). Also wires `app.state.rule_repo` and `app.state.candidate_repo` (synthesis repos that create their own sessions via SessionFactory).
- **Per-request resources** in `apps/api/src/dependencies.py`: DB sessions and domain services via `Depends()`. Services receive ports (repos, adapters) in `__init__`.

Note: IncidentService uses per-request session injection (`Depends`), while RuleRepo/CandidateRepo use app-level SessionFactory (`app.state`). This is intentional — synthesis routes operate outside the per-request lifecycle.

To add a new domain service: create the service in `packages/core/`, add a `get_*_service()` function in `dependencies.py` that wires ports to concrete adapters, then use `Annotated[Service, Depends(get_service)]` in route handlers.

### Tenant Isolation (RLS)

RLS middleware (`apps/api/src/middleware/rls.py`) extracts tenant from JWT or `X-API-Key`, sets PostgreSQL `app.tenant_id` session variable. All DB queries are automatically tenant-scoped. Admin requests (role=admin) set `is_admin=True` on request.state and bypass RLS for cross-tenant reads. Public paths (no tenant required): `/health`, `/ready`, `/docs`, `/openapi.json`, `/v1/tenants/register`.

### Web Auth (Firebase — `apps/web/`)

SvelteKit acts as BFF (Backend For Frontend) for Firebase Auth:
- **`src/lib/firebase.ts`** — Firebase client SDK singleton (browser-side)
- **`src/lib/server/firebase-admin.ts`** — Firebase Admin SDK singleton (server-side, ADC on Cloud Run)
- **`src/lib/server/auth.ts`** — `verifyAuthToken()` supporting `__session` cookie + Bearer token
- **`src/lib/server/users.ts`** — `getOrCreateUser()` JIT provisioning, ADMIN_EMAILS check
- **`src/hooks.server.ts`** — `authenticate` + `gateUser` sequence on every request
- **`src/routes/api/auth/session/+server.ts`** — POST (exchange idToken for session cookie) / DELETE (logout)
- **`src/routes/admin/`** — Admin cockpit (6 sections), server-side role guard in `+layout.server.ts`
- Session cookie: `__session`, 5-day, httpOnly, secure, SameSite=Lax

### Database Models (`packages/db/`)

`Base` model (`packages/db/src/models/base.py`) auto-generates snake_case table names, provides UUID `id`, `created_at`, `updated_at` on all models. Uses legacy `Column()` style (with `__allow_unmapped__ = True`), not `Mapped[]` annotations. Domain entities in `packages/core/` are frozen Pydantic models — DB models and domain entities are separate.

`User` model has `firebase_uid` (unique, indexed) linking to Firebase Auth, `display_name`, `email_verified`, `last_login`, and nullable `tenant_id` (JIT-provisioned users start without a tenant). Migrations: 001 (initial), 002 (waitlist), 003 (false positive fields), 004 (Firebase auth fields).

### Semgrep Rules (`packages/semgrep-rules/`)

10 categories: unsafe-regex, injection, deployment-error, missing-safety-check, race-condition, unsafe-api-usage, resource-exhaustion, data-consistency, missing-error-handling, cascading-failure.

Rule ID format: `{category}-{NNN}` (e.g., `unsafe-regex-001`). Each rule YAML requires: id, message, severity, languages, pattern.

### Deploy Pipeline

**Trunk-Based CD — single environment (prod).**

- CI runs on every PR targeting `main` (lint + mypy + tests + semgrep)
- Merging to `main` triggers automatic deploy to prod: API (`muscle-prod-api`) + Web (`muscle-prod-web`)
- Domain: `muscle.oute.pro` (web + API via BFF), `mcp.muscle.oute.pro` (MCP)
- No staging environment — CI quality gates are the only barrier before prod
- Uses Workload Identity Federation — no service account keys
- Artifact Registry: `muscle-prod-docker` (images: `muscle-api`, `muscle-web`)

Flow: `feature branch → PR → CI → merge main → deploy prod (API + Web)`

Branch protection on `main` (configure in GitHub Settings → Branches):
- Require PR before merging
- Require CI status checks to pass

## ⛔ MASTER RULES — IMMUTABLE

This section contains constitutional constraints for this project. Rules here are non-negotiable and cannot be altered by the AI or by the user in a single request.

### Protocol to change any Master Rule

1. **First request**: state which rule you want to change and why.
2. **AI must restate** the current rule, the proposed change, and the risks involved.
3. **Second request**: explicit confirmation ("yes, confirm the change").

If the AI suggests or implements any change to a Master Rule without receiving two explicit confirmations, that is a violation and the change must be reverted. This protocol applies to both the AI and the user — neither can bypass it unilaterally.

---

### MASTER RULE 1 — Gitflow: Trunk-Based CD (prod only)

**Ratified**: 2026-03-29

1. **Single environment**: only `prod` exists. No staging, no dev, no preview environments.
2. **No direct push to main**: every change must come through a PR.
3. **CI must pass before merge**: lint + mypy + tests + semgrep — all green.
4. **Merge to main = deploy prod**: automatic, no manual tags, no manual triggers.
5. **No version tags for deploy**: tags may be used for releases/changelog only, never as deploy triggers.

No docker-compose — local development uses `make dev` directly. Dockerfiles exist per app (`apps/api/Dockerfile`, `apps/web/Dockerfile`, `apps/mcp/Dockerfile`) for Cloud Run deployment only. Local DB requires a standalone PostgreSQL instance or Cloud SQL Auth Proxy.

### MASTER RULE 2 — Resource Isolation: muscle-* namespace (no oute-* sharing)

**Ratified**: 2026-03-29

1. **All GCP resources MUST use the `muscle-` prefix**: Cloud Run services (`muscle-prod-api`, `muscle-prod-web`), Artifact Registry (`muscle-prod-docker`), service accounts (`muscle-prod-gh-actions`), WIF pools (`muscle-prod-gh-pool`), secrets (`muscle-prod-db-password`).
2. **NEVER use the `oute-` or `oute-prod-` prefix** for any resource in this project. That namespace belongs to the oute.me project.
3. **Shared resources (exceptions)**: only the GCP project ID (`oute-488706`), the Cloud SQL instance, and the Firebase Auth project are shared with oute.me. Everything else is isolated.
4. **URLs MUST use `muscle.oute.pro`** as the canonical domain. Never reference raw Cloud Run URLs (`*.a.run.app`) in code, docs, or config.
5. **Terraform name_prefix**: `infra/gcp/main.tf` MUST use `"muscle-${var.environment}"`. Any change to this prefix is a Master Rule violation.

## Code Style

### Python
- Line length: 100
- Ruff rules: E, W, F, I, N, UP, B, C4, PTH, RUF
- 4-space indent, double quotes
- `asyncio_mode = "auto"` in pytest (no need for `@pytest.mark.asyncio`)
- Per-file Ruff ignores: `S101` in tests, `B008` in routes (FastAPI `Depends()`), relaxed rules in Semgrep test fixtures

### Frontend
- 2-space indent, TypeScript strict
- `no-explicit-any` is an error
- Unused args prefixed with `_` (e.g., `_event`)
- Path aliases: `$lib`, `$components`

### Pre-commit Hooks
Ruff (lint + format), mypy strict on `packages/core/`, Semgrep on staged Python files, plus standard checks (trailing whitespace, EOF, YAML/JSON, no large files >500KB).

## Conventions

- Commits: Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`)
- Code + public docs: English. Internal docs: PT-BR
- Branch naming: sequential `NNN-short-name` (auto-incremented)
- Tasks format: `- [ ] TXXX [P] [USY] Description with file path`

## SpecKit Workflow

This project uses SpecKit v0.4.3 for structured feature development:

1. `/speckit.constitution` → `/speckit.specify` → `/speckit.clarify` → `/speckit.plan` → `/speckit.tasks` → `/speckit.analyze` → `/speckit.implement`

Design artifacts live in `specs/{feature-name}/`. Key scripts in `.specify/scripts/bash/`:
- `create-new-feature.sh` — Creates feature branch + spec directory
- `check-prerequisites.sh` — Validates feature context

## Active Technologies
- Python 3.12+ (API), TypeScript strict (Web, SvelteKit) + firebase (client SDK), firebase-admin (server SDK), @sveltejs/adapter-node (237-admin-auth-domain)
- PostgreSQL 16 + pgvector (Cloud SQL) — existing (237-admin-auth-domain)

## Recent Changes
- 237-admin-auth-domain: Added Python 3.12+ (API), TypeScript strict (Web, SvelteKit) + firebase (client SDK), firebase-admin (server SDK), @sveltejs/adapter-node
