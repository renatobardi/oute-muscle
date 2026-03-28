# Implementation Plan: Incident-Based Code Guardrails Platform

**Branch**: `001-incident-code-guardrails` | **Date**: 2026-03-28 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-incident-code-guardrails/spec.md`

## Summary

Build an incident-based code guardrails platform that prevents production incidents from recurring via 3 detection layers: deterministic Semgrep rules (blocking), RAG advisory on PRs (consultive), and automatic rule synthesis (progressive). Delivered through GitHub App, MCP Server, and REST API. Monorepo architecture with FastAPI backend, SvelteKit dashboard, PostgreSQL+pgvector for knowledge base, and Vertex AI for hybrid LLM routing (Gemini Flash/Pro + Claude Sonnet 4).

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript strict (frontend)
**Primary Dependencies**: FastAPI, asyncpg, pgvector, google-cloud-aiplatform, PyGithub, pydantic v2, uvicorn (backend); SvelteKit, Tailwind CSS, shadcn-svelte (frontend)
**Storage**: PostgreSQL 16 with pgvector extension (Cloud SQL), HNSW indexes, Row-Level Security
**Testing**: pytest + pytest-asyncio (backend), vitest + playwright (frontend), Semgrep rule test files (co-located)
**Target Platform**: GCP Managed Services — Cloud Run (API + dashboard), Cloud Run Job (RAG worker), Cloud SQL, Vertex AI, Secret Manager, Artifact Registry, Cloud Tasks
**Project Type**: Multi-service web platform (API + dashboard + MCP server + workers)
**Performance Goals**: Pre-commit <2s/500 lines, CI <30s overhead, RAG triage <3s, search <2s, MCP tools <5s
**Constraints**: Zero customer code at rest, all secrets in GCP Secret Manager, Vertex AI IAM only (no external API keys), SOC 2 readiness
**Scale/Scope**: 100 concurrent tenants, 50 contributors each, 10,000 incidents per knowledge base, 5 supported languages

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Product Mission | PASS | Every component serves incident prevention |
| II. Incident Traceability | PASS | FR-003: every rule links to incident. Schema enforces chain |
| III. Three-Layer Detection | PASS | L1 blocking, L2 consultive, L3 progressive — all per spec |
| IV. Architecture & Infrastructure | PASS | GCP-only: Cloud Run, Cloud SQL, Vertex AI. No VMs/K8s |
| V. Hybrid LLM Strategy | PASS | Gemini Flash ~70%, Pro ~15%, Claude Sonnet 4 ~15% via Vertex AI |
| VI. Data Privacy & Multi-Tenancy | PASS | RLS, pgvector partitioned by tenant_id, no code at rest (FR-027) |
| VII. Quality Gates | PASS | TDD, 80% coverage, mandatory Semgrep test files, Ruff + mypy strict |
| VIII. Security Posture | PASS | Secret Manager, Workload Identity, HMAC-SHA256 webhooks, rate limiting |
| IX. Delivery Channels & Open-Core | PASS | GitHub App + MCP Server + REST API. Open-core pricing per spec |
| X. Clean Architecture & Hexagonal | PASS | Hex boundaries at: LLM router (3 providers), delivery channels (3), GCP adapters (Cloud SQL, Vertex AI, Secret Manager). No speculative interfaces |
| XI. Incremental Complexity | PASS | L1 first, L2 after L1 proven, L3 after L2 proven. No Enterprise features pre-customer |
| XII. Observability | PASS | Structured JSON logging, correlation IDs, GCP-native (Cloud Logging/Trace/Monitoring) |

**Gate result**: ALL PASS — proceed to Phase 0.

*Post-Phase 1 re-check*: ALL PASS. Hexagonal boundaries applied only at real domain boundaries (LLM router with 3 providers, 3 delivery channels, GCP adapters) per Principle X. No speculative interfaces. Complexity justified in tracking table below.

## Project Structure

### Documentation (this feature)

```text
specs/001-incident-code-guardrails/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── api-rest.md
│   ├── api-github-webhook.md
│   ├── api-mcp-tools.md
│   └── api-internal.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
apps/
├── api/                          # FastAPI backend
│   ├── src/
│   │   ├── main.py               # FastAPI app entry point
│   │   ├── config.py             # Settings from Secret Manager
│   │   ├── dependencies.py       # DI container for ports/adapters
│   │   ├── middleware/
│   │   │   ├── auth.py           # JWT + API key validation
│   │   │   ├── rls.py            # Tenant context injection for RLS
│   │   │   ├── rate_limit.py     # Per-tier rate limiting
│   │   │   └── correlation.py    # Request tracing correlation IDs
│   │   ├── routes/
│   │   │   ├── incidents.py      # CRUD + search endpoints
│   │   │   ├── rules.py          # Rule management endpoints
│   │   │   ├── scans.py          # Scan trigger + results
│   │   │   ├── webhooks.py       # GitHub webhook handler (HMAC-SHA256)
│   │   │   ├── tenants.py        # Tenant + user management
│   │   │   ├── auth.py           # OAuth 2.1 + session endpoints
│   │   │   └── health.py         # Health + readiness probes
│   │   └── workers/
│   │       ├── rag_worker.py     # RAG advisory pipeline (Cloud Run Job)
│   │       └── synthesis.py      # Rule synthesis pipeline (Cloud Tasks)
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── conftest.py
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── alembic.ini               # Points to packages/db migrations
│
├── web/                          # SvelteKit dashboard
│   ├── src/
│   │   ├── routes/
│   │   │   ├── (dashboard)/      # Authenticated routes
│   │   │   │   ├── incidents/    # Incident CRUD + search
│   │   │   │   ├── rules/        # Rule management + approval queue
│   │   │   │   ├── scans/        # Scan results + trends
│   │   │   │   ├── settings/     # Tenant config + team + billing
│   │   │   │   └── audit/        # Audit log (Enterprise)
│   │   │   ├── auth/             # Login, callback, register
│   │   │   └── +layout.svelte
│   │   ├── lib/
│   │   │   ├── components/       # shadcn-svelte + custom components
│   │   │   ├── api/              # API client (typed fetch wrappers)
│   │   │   └── stores/           # Svelte stores (auth, tenant context)
│   │   └── app.html
│   ├── tests/
│   │   ├── unit/                 # vitest
│   │   └── e2e/                  # playwright
│   ├── Dockerfile
│   ├── package.json
│   ├── svelte.config.js
│   ├── tailwind.config.js
│   └── tsconfig.json
│
└── mcp/                          # MCP Server (Streamable HTTP)
    ├── src/
    │   ├── main.py               # MCP server entry point
    │   ├── tools/
    │   │   ├── scan_code.py
    │   │   ├── get_incident_advisory.py
    │   │   ├── synthesize_rules.py
    │   │   ├── list_relevant_incidents.py
    │   │   └── validate_fix.py
    │   ├── auth/                 # OAuth 2.1 Authorization Code + PKCE
    │   │   ├── provider.py
    │   │   └── middleware.py
    │   └── metering.py           # Usage tracking (50 free/month)
    ├── tests/
    ├── Dockerfile
    └── pyproject.toml

packages/
├── core/                         # Shared domain logic (hexagonal domain layer)
│   ├── src/
│   │   ├── domain/
│   │   │   ├── incidents/        # Incident entity, value objects, domain services
│   │   │   ├── rules/            # Rule entity, synthesis logic
│   │   │   ├── scanning/         # Scan orchestration, finding model
│   │   │   └── advisory/         # RAG pipeline, risk scoring
│   │   ├── ports/                # Port interfaces (hexagonal boundaries)
│   │   │   ├── llm.py            # LLM port (3 implementations: Flash, Pro, Claude)
│   │   │   ├── embedding.py      # Embedding port
│   │   │   ├── incident_repo.py  # Incident repository port
│   │   │   ├── rule_repo.py      # Rule repository port
│   │   │   ├── vector_search.py  # Vector search port
│   │   │   └── github.py         # GitHub API port
│   │   └── adapters/             # Adapter implementations
│   │       ├── vertex_llm.py     # Vertex AI adapter (Gemini Flash/Pro + Claude)
│   │       ├── vertex_embedding.py
│   │       ├── pg_incident_repo.py
│   │       ├── pg_rule_repo.py
│   │       ├── pg_vector_search.py
│   │       └── github_adapter.py # PyGithub adapter
│   ├── tests/
│   └── pyproject.toml
│
├── db/                           # Database models + migrations
│   ├── src/
│   │   ├── models/               # SQLAlchemy models with RLS
│   │   │   ├── incident.py
│   │   │   ├── rule.py
│   │   │   ├── tenant.py
│   │   │   ├── user.py
│   │   │   ├── finding.py
│   │   │   ├── scan.py
│   │   │   ├── audit_log.py
│   │   │   └── base.py           # RLS-aware base model
│   │   ├── migrations/           # Alembic migrations
│   │   │   └── versions/
│   │   └── session.py            # asyncpg session factory with tenant context
│   ├── alembic.ini
│   ├── tests/
│   └── pyproject.toml
│
└── semgrep-rules/                # Semgrep rules organized by category
    ├── rules/
    │   ├── unsafe-regex/
    │   │   ├── unsafe-regex-001.yaml
    │   │   └── unsafe-regex-001.test.py
    │   ├── race-condition/
    │   ├── missing-error-handling/
    │   ├── injection/
    │   ├── resource-exhaustion/
    │   ├── missing-safety-check/
    │   ├── deployment-error/
    │   ├── data-consistency/
    │   ├── unsafe-api-usage/
    │   └── cascading-failure/
    ├── metadata/                  # Rule metadata (incident links, versioning)
    │   └── registry.json          # Rule registry: ID → incident_id, revision
    └── tests/
        └── run_tests.sh           # Semgrep --test runner

infra/
└── gcp/
    ├── main.tf                   # Cloud Run, Cloud SQL, Vertex AI, Secret Manager
    ├── variables.tf
    ├── outputs.tf
    ├── modules/
    │   ├── cloud-run/
    │   ├── cloud-sql/
    │   ├── vertex-ai/
    │   ├── secret-manager/
    │   ├── artifact-registry/
    │   └── iam/                  # Workload Identity Federation
    └── environments/
        ├── dev.tfvars
        ├── staging.tfvars
        └── prod.tfvars

scripts/
├── seed-knowledge-base.py        # Ingest danluu/post-mortems + VOID
├── sync-rules.py                 # Sync rules to GitHub App / API
└── dev-setup.sh                  # Local dev environment setup

.github/
├── workflows/
│   ├── ci.yml                    # Lint + test + build (all apps/packages)
│   ├── deploy.yml                # Deploy to Cloud Run (staging/prod)
│   └── semgrep-scan.yml          # Semgrep scan + SARIF upload
└── dependabot.yml
```

**Structure Decision**: Monorepo with `apps/` for deployable services (api, web, mcp), `packages/` for shared code (core domain, db, semgrep-rules), `infra/` for Terraform, and `scripts/` for CLI tooling. Hexagonal architecture lives in `packages/core/` with ports and adapters at real domain boundaries (LLM, embedding, repositories, GitHub API).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| 3 deployable apps (api, web, mcp) | Each serves a distinct delivery channel with different protocols (HTTP/REST, SvelteKit SSR, MCP Streamable HTTP) | A single app would mix concerns; Cloud Run scales each independently |
| Hexagonal ports for LLM (3 providers) | Constitution V mandates hybrid LLM with Gemini Flash/Pro + Claude Sonnet 4 | Direct calls would scatter provider logic; router needs a common interface |
| Hexagonal ports for delivery channels | Constitution IX mandates 3 channels; each has distinct auth + protocol | Shared route handlers would create unmaintainable conditional logic |
