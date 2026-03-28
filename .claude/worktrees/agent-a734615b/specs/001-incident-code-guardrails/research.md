# Research: Incident-Based Code Guardrails Platform

**Branch**: `001-incident-code-guardrails` | **Date**: 2026-03-28

## R1: Semgrep Rule Authoring & SARIF Output

**Decision**: Semgrep YAML rules with custom metadata fields for incident traceability. SARIF 2.1.0 output via `semgrep --sarif`.

**Rationale**: Semgrep natively supports YAML rule definitions with `metadata` blocks for arbitrary key-value pairs (incident_id, source_url, severity, remediation). The `--sarif` flag produces standard SARIF 2.1.0 that GitHub Code Scanning consumes directly. No custom SARIF transformation needed.

**Alternatives considered**:
- CodeQL: More powerful for dataflow analysis but requires compilation for some languages, slower execution, and tied to GitHub ecosystem. Not suitable for <2s pre-commit hooks.
- Custom AST parser: Maximum flexibility but enormous engineering effort. Semgrep covers the pattern-matching needs for all 10 categories.

**Key findings**:
- Semgrep `metadata` block supports: `incident_id`, `source_url`, `severity`, `category`, `remediation`, `cwe`, `owasp` — all flow into SARIF `properties`.
- Rule test format: co-located `.test.py` (or `.test.js`, etc.) files with `# ruleid:` and `# ok:` annotations.
- Semgrep CI runs in ~5-15s for a typical repo; pre-commit on staged files only is well within 2s budget.
- SARIF upload to GitHub: `github/codeql-action/upload-sarif@v3` action, auto-populates Security Tab.

## R2: pgvector Similarity Search with HNSW and Multi-Tenancy

**Decision**: pgvector with HNSW indexes partitioned by tenant_id. VECTOR(768) for text-embedding-005 outputs. Cosine distance for similarity.

**Rationale**: pgvector in PostgreSQL 16 supports HNSW indexing for approximate nearest neighbor search. Combined with RLS, this provides tenant-isolated vector search without a separate vector database. HNSW offers better recall than IVFFlat at similar query speeds.

**Alternatives considered**:
- Pinecone/Weaviate/Qdrant: Dedicated vector DBs with better scaling at millions of vectors, but add operational complexity, a separate data store to secure, and don't integrate with RLS. At 10K incidents per tenant, pgvector is more than sufficient.
- IVFFlat index: Faster to build but lower recall. HNSW is preferred for knowledge bases where recall matters more than index build time.

**Key findings**:
- HNSW index creation: `CREATE INDEX ON incidents USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)`.
- Partition strategy: partial indexes per tenant_id, or a single index with tenant_id filter in query. For <100 tenants, single index with filter is simpler and sufficient.
- text-embedding-005 outputs 768-dimensional vectors. Cost: $0.10/MTok.
- Query pattern: `SELECT * FROM incidents WHERE tenant_id = $1 OR tenant_id IS NULL ORDER BY embedding <=> $2 LIMIT 10`.

## R3: Vertex AI Hybrid LLM Routing

**Decision**: Internal router in `packages/core` that computes a composite risk score and routes to the appropriate Vertex AI model. All models accessed via `google-cloud-aiplatform` SDK with service account auth.

**Rationale**: Vertex AI provides unified billing, IAM, and monitoring for Gemini Flash, Gemini Pro, and Claude Sonnet 4 (via Model Garden). A single service account authenticates all model calls. The router is a domain service with an LLM port that has 3 adapter implementations.

**Alternatives considered**:
- Direct Anthropic API for Claude: Requires separate API keys, billing, and monitoring. Violates Constitution VIII (no external API keys).
- Single model for all: Cheaper but doesn't optimize cost/quality tradeoff. Flash handles ~70% at $0.30/MTok vs Pro at $1.25/MTok vs Claude at $3.00/MTok.

**Key findings**:
- Risk score computation (FR-017): `score = (layer1_findings * 3) + (sensitive_path_count * 2) + (diff_lines > 500 ? 2 : 0) + (high_risk_categories * 4)`. Thresholds: low < 5, medium 5-12, high > 12.
- Vertex AI SDK: `vertexai.generative_models.GenerativeModel` for Gemini, `anthropic[vertex]` for Claude via Vertex.
- Fallback chain: Flash → Pro → Claude. If a model times out (30s), fall back to next tier.
- Token limits: Flash 1M context, Pro 1M context, Claude 200K context. For diffs up to 3K lines, all models handle the input comfortably.

## R4: GitHub App Integration & Webhook Security

**Decision**: GitHub App with webhook endpoint, HMAC-SHA256 signature verification, and Check Runs API for reporting.

**Rationale**: GitHub Apps are the recommended integration pattern for organizations. They provide granular permissions, installation-level access, and webhook delivery. HMAC-SHA256 verification ensures webhook authenticity per Constitution VIII.

**Alternatives considered**:
- GitHub OAuth App: Limited to user-level permissions, no org-wide installation.
- GitHub Actions only: Can't provide real-time PR review comments; only check status.

**Key findings**:
- Required permissions: `checks:write`, `pull_requests:write`, `contents:read`, `security_events:write`.
- Webhook events: `pull_request.opened`, `pull_request.synchronize`, `push`.
- Signature verification: Compare `X-Hub-Signature-256` header with HMAC-SHA256 of payload using shared secret from Secret Manager.
- Check Runs API: Create check run on PR with SARIF annotations for inline findings.
- Rate limits: GitHub API allows 5,000 req/hour per installation. Sufficient for 100 tenants.

## R5: MCP Server with Streamable HTTP & OAuth 2.1

**Decision**: Python MCP SDK with Streamable HTTP transport. OAuth 2.1 Authorization Code + PKCE flow with the platform as its own authorization server. JWT access tokens verified locally.

**Rationale**: MCP specification mandates Streamable HTTP for server-to-client communication. OAuth 2.1 with PKCE is the standard for public clients (IDE extensions). Self-hosted auth server avoids dependency on third-party OAuth providers for MCP-specific flows.

**Alternatives considered**:
- SSE transport: Deprecated in MCP spec in favor of Streamable HTTP.
- Third-party OAuth (Auth0, Okta): Adds cost and dependency for a simple token-based flow. Platform already needs user auth for dashboard.

**Key findings**:
- Python MCP SDK: `mcp` package supports Streamable HTTP transport.
- 5 tools: scan_code, get_incident_advisory, synthesize_rules, list_relevant_incidents, validate_fix.
- Metering: Track tool calls per tenant per month in PostgreSQL. Check quota before execution.
- JWT: RS256 signed, 1h expiry. Refresh token: opaque, 30d expiry, stored hashed in DB.

## R6: Multi-Tenancy via PostgreSQL Row-Level Security

**Decision**: RLS policies on all tenant-scoped tables. Tenant context set via `SET LOCAL` on each connection from asyncpg pool. Shared knowledge base rows have `tenant_id IS NULL`.

**Rationale**: RLS is the most robust tenant isolation at the database level. It's transparent to application code — queries automatically filter by tenant. Shared rows (public knowledge base) use NULL tenant_id with `OR tenant_id IS NULL` in policies.

**Alternatives considered**:
- Schema-per-tenant: Maximum isolation but unmanageable at 100+ tenants. Migrations become O(N).
- Application-level filtering: Error-prone; a single missed WHERE clause leaks data.

**Key findings**:
- Policy: `CREATE POLICY tenant_isolation ON incidents USING (tenant_id = current_setting('app.tenant_id')::uuid OR tenant_id IS NULL)`.
- Session setup: `SET LOCAL "app.tenant_id" = '<uuid>'` on each request via middleware.
- asyncpg pool: Use `connection.execute("SET LOCAL ...")` in a transaction context per request.
- Migrations: RLS policies applied in Alembic migrations alongside table creation.

## R7: Monorepo Tooling & CI/CD

**Decision**: Python monorepo with workspace-level pyproject.toml, apps and packages as subdirectories. Node.js workspace for SvelteKit frontend. GitHub Actions with Workload Identity Federation for GCP deployment.

**Rationale**: Monorepo keeps all code, rules, and infrastructure in one repository for atomic changes. Separate pyproject.toml per package allows independent dependency management while sharing a common virtual environment for development.

**Alternatives considered**:
- Polyrepo: Separate repos for api, web, rules. Adds cross-repo coordination overhead and breaks atomic deployments.
- Nx/Turborepo: Overkill for 3 Python apps + 1 SvelteKit app. Simple Makefile + GitHub Actions matrix is sufficient.

**Key findings**:
- Python: Each package has its own `pyproject.toml`. Development uses `pip install -e packages/core -e packages/db` for editable installs.
- Frontend: `apps/web/package.json` is standalone. No need for npm workspaces with a single frontend.
- CI: GitHub Actions matrix builds each app in parallel. Shared packages are installed as dependencies.
- Deploy: Docker multi-stage builds per app. Cloud Run deploys via `gcloud run deploy` with Workload Identity.
- semantic-release: Conventional Commits drive version bumps and changelogs.

## R8: Structured Logging & Observability

**Decision**: Python `structlog` for JSON-formatted logs. GCP Cloud Logging auto-ingests structured JSON from Cloud Run stdout. Cloud Trace for distributed tracing via OpenTelemetry. Cloud Monitoring for custom metrics.

**Rationale**: Cloud Run logs stdout as structured JSON to Cloud Logging automatically. structlog provides clean JSON output with minimal configuration. OpenTelemetry is the standard for distributed tracing and integrates with Cloud Trace.

**Alternatives considered**:
- ELK stack: Self-managed, contradicts GCP-only infrastructure principle.
- Datadog/New Relic: Third-party cost and dependency when GCP-native tooling covers the needs.

**Key findings**:
- structlog config: JSON renderer, add correlation_id, tenant_id, user_id to every log line.
- Correlation ID: Generated in middleware, propagated via `contextvars` to all async calls.
- Metrics: `google-cloud-monitoring` SDK for custom metrics (LLM latency, rule match rates, tenant usage).
- Tracing: `opentelemetry-exporter-gcp-trace` for spans across API → LLM → DB.
