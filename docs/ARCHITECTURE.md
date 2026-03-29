# Architecture

Oute Muscle is a monorepo organized around hexagonal architecture principles. This document covers system design, component boundaries, data flow, and key decisions.

## High-level overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client layer                            │
│  SvelteKit dashboard (apps/web)    MCP Server (apps/mcp)        │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS / WebSocket
┌──────────────────────────▼──────────────────────────────────────┐
│                       API layer (apps/api)                      │
│  FastAPI  ·  Middleware stack  ·  Route handlers  ·  Workers    │
└──────┬───────────────────┬────────────────────────┬─────────────┘
       │                   │                        │
┌──────▼──────┐  ┌─────────▼──────────┐  ┌─────────▼───────────┐
│ packages/   │  │ packages/db/       │  │ External services    │
│ core/       │  │ SQLAlchemy models  │  │                      │
│ domain/     │  │ Alembic migrations │  │ Vertex AI (LLM)      │
│ ports/      │  │ asyncpg driver     │  │ Semgrep (scanning)   │
│ adapters/   │  │                    │  │ GitHub (webhooks)    │
└──────┬──────┘  └─────────┬──────────┘  └──────────────────────┘
       │                   │
┌──────▼───────────────────▼──────────────────────────────────────┐
│                    PostgreSQL 16 + pgvector                     │
│    Cloud SQL (oute-postgres)  ·  HNSW indexes  ·  RLS          │
└─────────────────────────────────────────────────────────────────┘
```

## Monorepo structure

### `packages/core/` — Hexagonal domain

The only package with zero framework dependencies. Depends only on Pydantic.

```
packages/core/src/
  domain/       Pure business logic, value objects, domain errors
  ports/        Abstract interfaces (ABCs) for all external dependencies
  adapters/     Concrete implementations of ports
```

**Boundary rule**: nothing outside `packages/core/adapters/` may import from `packages/core/domain/` directly. All cross-boundary communication goes through ports.

**Adapters that exist**:
- `VertexGeminiFlash` / `VertexGeminiPro` / `VertexClaudeSonnet` — LLM adapters (implements `LLMPort`)
- `VertexAIEmbedding` — generates embeddings via `text-embedding-005` (implements `EmbeddingPort`)
- `PostgreSQLIncidentRepo` — incident persistence (implements `IncidentRepoPort`)
- `PostgreSQLRuleRepo` — rule persistence (implements `RuleRepoPort`)
- `PostgreSQLVectorSearch` — pgvector HNSW similarity search (implements `VectorSearchPort`)
- `GitHubAdapter` — GitHub App API integration (implements `GitHubPort`)

### `apps/api/` — FastAPI backend

```
apps/api/src/
  main.py         App factory, DI container, lifespan, route registration
  config.py       Pydantic BaseSettings (env vars)
  routes/         One router per domain area
  middleware/     CORS, rate_limit, correlation (global); auth, rls, webhook_auth (route-level)
  workers/        Background tasks (synthesis, RAG ingestion, retention)
```

**Middleware registered** (in `main.py`, outer → inner):
1. `CORSMiddleware` — allows all origins (dev/beta phase)
2. `RateLimitMiddleware` — per-tenant request throttling (in-memory sliding window)
3. `CorrelationMiddleware` — injects `X-Correlation-ID` for distributed tracing

**Route-level dependencies** (not global middleware):
- `auth.py` — `require_api_key()` function via `Depends()`, validates `X-API-Key`
- `webhook_auth.py` — `verify_webhook_signature()` utility for GitHub HMAC-SHA256
- `rls.py` — `RLSMiddleware` class exists but is **not yet registered** in `main.py`

### `packages/db/` — Data layer

SQLAlchemy 2.0 (async) models and Alembic migrations.

**Key tables**:
- `tenants` — multi-tenant root, plan tier, slug
- `users` — users per tenant, email, role (admin/editor/viewer)
- `incidents` — post-mortem entries, category, severity, embedding vector (768D)
- `semgrep_rules` — Semgrep rules, linked to incidents, yaml_content, test_file_content
- `scans` — scan runs, status, trigger source, risk score
- `findings` — per-file findings from scans, linked to rules
- `advisories` — L2 RAG advisory results, confidence, reasoning
- `synthesis_candidates` — L3 candidates, status (pending_review/approved/rejected/failed)
- `audit_log_entries` — audit trail, action, entity, changes (JSONB)

Note: there is no `waitlist` DB model — the waitlist route uses direct SQL insert.

**Row-Level Security**: all tenant-scoped tables have RLS policies enforcing `app.tenant_id`. The RLS middleware (when registered) sets this per request via `SET LOCAL`.

### `packages/semgrep-rules/` — Detection rules

10 categories under `rules/`, each with numbered rules (`{category}-{NNN}.yaml`) and mandatory test files (`{category}-{NNN}.test.py`).

```
packages/semgrep-rules/
  rules/
    unsafe-regex/
      unsafe-regex-001.yaml
      unsafe-regex-001.test.py
    injection/
    race-condition/
    ...
  metadata/
    registry.json
  tests/
    run_tests.sh
    test_scan_runner.py
```

**Every rule must include**:
- `id` — unique, format `{category}-{NNN}`
- `message` — what went wrong and how to fix it
- `severity` — ERROR / WARNING / INFO
- `languages` — target language(s)
- `pattern` / `pattern-either` / `patterns`
- A link to the originating incident in `metadata.incident_url`

## Three-layer detection

### L1 — Semgrep (blocking)

Runs in CI via `.github/workflows/ci.yml` on every PR. Blocks merge on any ERROR severity finding. Rules are static YAML — fast, deterministic, zero cost per run.

**How a rule reaches L1**:
1. Incident documented via API
2. L3 synthesis proposes a Semgrep rule
3. Engineer reviews and approves
4. Rule merged to `packages/semgrep-rules/`
5. CI picks it up on next PR

### L2 — RAG advisory (consultive)

When a scan runs, each code chunk is embedded and similarity-searched against the `incidents` table vector index. Findings above the similarity threshold are returned as advisory comments — not blocking.

**Embedding model**: `text-embedding-005` (768 dimensions), stored in pgvector with HNSW index.

### L3 — Auto-synthesis (progressive)

Background worker triggered when the RAG layer surfaces a high-similarity hit without a corresponding L1 rule. Uses Vertex AI Gemini 2.5 Pro to:
1. Analyze the incident and the offending code
2. Draft a Semgrep rule
3. Create a rule candidate (status: `pending_review`)
4. Engineer reviews in dashboard → promotes to L1 or discards

## Infrastructure (GCP)

```
GCP Project: oute-488706
Region: us-central1

Cloud Run:
  muscle-prod-api  (min: 0, max: 10 instances)

Cloud SQL:
  oute-postgres (shared PostgreSQL 16 instance)
    database: oute_muscle_prod
    user: muscle_app

Artifact Registry:
  us-central1-docker.pkg.dev/oute-488706/muscle-prod-docker

Secret Manager:
  muscle-prod-db-password

Terraform state:
  gs://oute-terraform-state/oute-muscle/prod/
```

**Auth model**: Workload Identity Federation (no service account keys). GitHub Actions authenticates as `muscle-prod-gh-actions@oute-488706.iam.gserviceaccount.com` via OIDC token exchange.

## CI/CD pipeline

```
PR → main (CI gate)
  └── ci.yml
        ├── lint (ruff + eslint)
        ├── type-check (mypy + svelte-check)
        ├── test (pytest, coverage reported via codecov)
        ├── test-rules (semgrep --test)
        └── semgrep-scan.yml (Semgrep rules on changed files)

merge main → deploy prod (automatic)
  └── deploy.yml
        ├── build Docker image
        ├── push to Artifact Registry (muscle-prod-docker)
        ├── run migrations (alembic upgrade head → oute_muscle_prod)
        ├── deploy to Cloud Run (muscle-prod-api)
        └── readiness probe (/health/live — 60s timeout)
```

## Observability

- **Structured logging**: `structlog` with JSON output, GCP Cloud Logging compatible. Context vars auto-injected: `correlation_id`, `tenant_id`, `user_id`.
- **Distributed tracing**: OpenTelemetry with GCP Cloud Trace exporter. Auto-instruments FastAPI (ASGI), SQLAlchemy (queries), HTTPX (outbound calls).
- **Health probes**: `/health/live` (liveness), `/health/ready` (DB + LLM check), `/health/startup` (boot complete).

## Key design decisions

**Why hexagonal architecture?**
`packages/core/` contains all business logic with zero framework deps. This means domain logic is testable without a database, HTTP server, or LLM client. Adapters are swappable — critical when the LLM landscape is moving fast.

**Why a shared Cloud SQL instance?**
Cost. The `oute-postgres` instance (`db-f1-micro`) hosts the `oute_muscle_prod` database. A dedicated instance per project would add ~$50/month. RLS ensures tenant data isolation within the database.

**Why Semgrep for L1 instead of building custom AST analysis?**
Semgrep handles multi-language parsing, has a large existing rule ecosystem, integrates natively with GitHub, and produces SARIF output. Building equivalent AST analysis for 10+ languages would be months of work.

**Why pgvector instead of a dedicated vector DB (Pinecone, Weaviate)?**
Fewer moving parts. The incident corpus is small (thousands of documents, not millions). PostgreSQL with HNSW indexes handles this workload without adding another managed service, another bill, and another failure domain.

**Why UV workspaces?**
UV resolves the entire monorepo lockfile in a single pass — much faster than pip and avoids version conflicts between packages. The `uv.lock` at the root pins all deps deterministically.
