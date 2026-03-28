# Tasks: Incident-Based Code Guardrails Platform

**Input**: Design documents from `/specs/001-incident-code-guardrails/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: TDD approach — test tasks precede implementation tasks per Constitution Principle VII.

**Organization**: Tasks are grouped by user story (P1→P7) per user request, with 8 phases aligned to delivery milestones.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Backend API**: `apps/api/src/`, `apps/api/tests/`
- **Frontend**: `apps/web/src/`, `apps/web/tests/`
- **MCP Server**: `apps/mcp/src/`, `apps/mcp/tests/`
- **Core domain**: `packages/core/src/`, `packages/core/tests/`
- **Database**: `packages/db/src/`, `packages/db/tests/`
- **Semgrep rules**: `packages/semgrep-rules/rules/`, `packages/semgrep-rules/tests/`
- **Infrastructure**: `infra/gcp/`
- **Scripts**: `scripts/`
- **CI/CD**: `.github/workflows/`

---

## Phase 1: Setup (Monorepo Initialization)

**Purpose**: Initialize monorepo structure, tooling, and shared configuration. No GCP dependency.

- [x] T001 Create monorepo root with pyproject.toml, Makefile, and .editorconfig at /
- [x] T002 [P] Initialize apps/api/ with pyproject.toml, FastAPI dependencies (fastapi, uvicorn, asyncpg, pydantic v2) in apps/api/pyproject.toml
- [x] T003 [P] Initialize apps/web/ with SvelteKit, TypeScript strict, Tailwind CSS, shadcn-svelte in apps/web/package.json
- [x] T004 [P] Initialize apps/mcp/ with pyproject.toml and MCP SDK dependency in apps/mcp/pyproject.toml
- [x] T005 [P] Initialize packages/core/ with pyproject.toml (domain logic, no framework deps) in packages/core/pyproject.toml
- [x] T006 [P] Initialize packages/db/ with pyproject.toml (SQLAlchemy, asyncpg, alembic) in packages/db/pyproject.toml
- [x] T007 [P] Initialize packages/semgrep-rules/ with directory structure for 10 categories in packages/semgrep-rules/rules/
- [x] T008 Configure Python linting (Ruff) and type checking (mypy strict) in pyproject.toml
- [x] T009 [P] Configure frontend linting (ESLint + eslint-plugin-svelte + Prettier) in apps/web/.eslintrc.cjs
- [x] T010 [P] Create .gitignore with Python, Node.js, and universal patterns at .gitignore
- [x] T011 [P] Create GitHub Actions CI workflow for lint + type-check + test in .github/workflows/ci.yml
- [x] T012 Create dev-setup.sh script for local environment initialization in scripts/dev-setup.sh

**Checkpoint**: All packages install, linting passes, CI workflow runs green on empty project.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared domain types, port interfaces, and base test infrastructure that ALL phases depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T013 Define incident category enum and severity enum as domain value objects in packages/core/src/domain/incidents/enums.py
- [x] T014 [P] Define Incident domain entity with all fields from data-model.md in packages/core/src/domain/incidents/entity.py
- [x] T015 [P] Define SemgrepRule domain entity with category-prefixed ID scheme in packages/core/src/domain/rules/entity.py
- [x] T016 [P] Define Finding and Advisory domain entities in packages/core/src/domain/scanning/entities.py
- [x] T017 [P] Define Scan domain entity with risk_level and composite score in packages/core/src/domain/scanning/scan.py
- [x] T018 Define LLM port interface (Protocol) with generate and generate_structured methods in packages/core/src/ports/llm.py
- [x] T019 [P] Define Embedding port interface in packages/core/src/ports/embedding.py
- [x] T020 [P] Define IncidentRepo port interface with CRUD + search + optimistic locking in packages/core/src/ports/incident_repo.py
- [x] T021 [P] Define RuleRepo port interface with create, list_active, toggle, next_sequence_number in packages/core/src/ports/rule_repo.py
- [x] T022 [P] Define VectorSearch port interface with find_similar in packages/core/src/ports/vector_search.py
- [x] T023 [P] Define GitHub port interface with get_pr_diff, create_check_run, post_review_comment, create_pr in packages/core/src/ports/github.py
- [x] T024 Implement compute_risk_score function (composite formula, thresholds low<5, med 5-12, high>12) in packages/core/src/domain/scanning/risk_score.py
- [x] T025 Write unit tests for compute_risk_score covering all threshold boundaries in packages/core/tests/test_risk_score.py
- [x] T026 Write unit tests for domain entity validation (Incident required fields, SemgrepRule ID format) in packages/core/tests/test_entities.py
- [x] T027 Create conftest.py with shared test fixtures for packages/core in packages/core/tests/conftest.py

**Checkpoint**: All domain entities defined, all port interfaces declared, risk score tests pass. Zero external dependencies.

---

## Phase 3: User Story 1 — Static Rule Scanning (Priority: P1) 🎯 MVP

**Goal**: 10 Semgrep rules with incident metadata + pre-commit hook + GitHub Action. Delivers Layer 1 value with zero GCP dependency.

**Independent Test**: Push code with a known anti-pattern (catastrophic regex), verify pre-commit blocks it and CI SARIF report appears.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T028 [P] [US1] Write Semgrep rule test for unsafe-regex-001 (catastrophic backtracking) in packages/semgrep-rules/rules/unsafe-regex/unsafe-regex-001.test.py
- [x] T029 [P] [US1] Write Semgrep rule test for race-condition-001 in packages/semgrep-rules/rules/race-condition/race-condition-001.test.py
- [x] T030 [P] [US1] Write Semgrep rule test for missing-error-handling-001 in packages/semgrep-rules/rules/missing-error-handling/missing-error-handling-001.test.py
- [x] T031 [P] [US1] Write Semgrep rule test for injection-001 in packages/semgrep-rules/rules/injection/injection-001.test.py
- [x] T032 [P] [US1] Write Semgrep rule test for resource-exhaustion-001 in packages/semgrep-rules/rules/resource-exhaustion/resource-exhaustion-001.test.py
- [x] T033 [P] [US1] Write Semgrep rule test for missing-safety-check-001 in packages/semgrep-rules/rules/missing-safety-check/missing-safety-check-001.test.py
- [x] T034 [P] [US1] Write Semgrep rule test for deployment-error-001 in packages/semgrep-rules/rules/deployment-error/deployment-error-001.test.py
- [x] T035 [P] [US1] Write Semgrep rule test for data-consistency-001 in packages/semgrep-rules/rules/data-consistency/data-consistency-001.test.py
- [x] T036 [P] [US1] Write Semgrep rule test for unsafe-api-usage-001 in packages/semgrep-rules/rules/unsafe-api-usage/unsafe-api-usage-001.test.py
- [x] T037 [P] [US1] Write Semgrep rule test for cascading-failure-001 in packages/semgrep-rules/rules/cascading-failure/cascading-failure-001.test.py
- [x] T038 [US1] Write integration test for Semgrep scan runner (scan file, assert SARIF output) in packages/semgrep-rules/tests/test_scan_runner.py

### Implementation for User Story 1

- [x] T039 [P] [US1] Create unsafe-regex-001.yaml rule with incident metadata (ID, URL, severity, category, remediation) in packages/semgrep-rules/rules/unsafe-regex/unsafe-regex-001.yaml
- [x] T040 [P] [US1] Create race-condition-001.yaml rule with incident metadata in packages/semgrep-rules/rules/race-condition/race-condition-001.yaml
- [x] T041 [P] [US1] Create missing-error-handling-001.yaml rule with incident metadata in packages/semgrep-rules/rules/missing-error-handling/missing-error-handling-001.yaml
- [x] T042 [P] [US1] Create injection-001.yaml rule with incident metadata in packages/semgrep-rules/rules/injection/injection-001.yaml
- [x] T043 [P] [US1] Create resource-exhaustion-001.yaml rule with incident metadata in packages/semgrep-rules/rules/resource-exhaustion/resource-exhaustion-001.yaml
- [x] T044 [P] [US1] Create missing-safety-check-001.yaml rule with incident metadata in packages/semgrep-rules/rules/missing-safety-check/missing-safety-check-001.yaml
- [x] T045 [P] [US1] Create deployment-error-001.yaml rule with incident metadata in packages/semgrep-rules/rules/deployment-error/deployment-error-001.yaml
- [x] T046 [P] [US1] Create data-consistency-001.yaml rule with incident metadata in packages/semgrep-rules/rules/data-consistency/data-consistency-001.yaml
- [x] T047 [P] [US1] Create unsafe-api-usage-001.yaml rule with incident metadata in packages/semgrep-rules/rules/unsafe-api-usage/unsafe-api-usage-001.yaml
- [x] T048 [P] [US1] Create cascading-failure-001.yaml rule with incident metadata in packages/semgrep-rules/rules/cascading-failure/cascading-failure-001.yaml
- [x] T049 [US1] Create rule registry JSON mapping rule IDs to incident IDs and revisions in packages/semgrep-rules/metadata/registry.json
- [x] T050 [US1] Create Semgrep test runner script (semgrep --test) in packages/semgrep-rules/tests/run_tests.sh
- [x] T051 [US1] Create pre-commit hook configuration (.pre-commit-config.yaml) that runs Semgrep on staged files in .pre-commit-config.yaml
- [x] T052 [US1] Create GitHub Action workflow for Semgrep scan + SARIF upload to Security Tab in .github/workflows/semgrep-scan.yml
- [x] T053 [US1] Verify all 10 rule tests pass via run_tests.sh in packages/semgrep-rules/tests/run_tests.sh

**Checkpoint**: 10 Semgrep rules with tests, pre-commit hook blocks anti-patterns in <2s, GitHub Action produces SARIF. Layer 1 MVP delivered — zero GCP dependency.

---

## Phase 4: User Story 2 — Incident Knowledge Base Management (Priority: P2)

**Goal**: PostgreSQL schema + incident CRUD + embedding generation + CLI seeding + audit log.

**Independent Test**: Ingest incident via CLI, verify it appears in DB with embedding, edit anti-pattern, confirm embedding regenerated and audit log recorded.

### API Entry Point (required by all subsequent phases)

- [x] T054 Create FastAPI app entry point with DI container, middleware stack, and route registration in apps/api/src/main.py

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T055 [P] [US2] Write unit tests for Incident domain service (create, update with optimistic locking, soft delete, link rule blocking) in packages/core/tests/test_incident_service.py
- [x] T056 [P] [US2] Write integration test for PostgreSQL incident repository (CRUD + optimistic locking + soft delete) in packages/db/tests/integration/test_pg_incident_repo.py
- [x] T057 [P] [US2] Write integration test for embedding generation on incident create/update in packages/core/tests/integration/test_embedding_service.py
- [x] T058 [P] [US2] Write integration test for pgvector similarity search in packages/db/tests/integration/test_vector_search.py
- [x] T059 [P] [US2] Write unit tests for audit log recording on all mutation operations in packages/db/tests/test_audit_log.py
- [x] T060 [US2] Write integration test for CLI ingestion (--url, --file, --auto-approve, --dry-run) in scripts/tests/test_seed_cli.py

### Implementation for User Story 2

- [x] T061 [US2] Create SQLAlchemy base model with RLS-aware session management in packages/db/src/models/base.py
- [x] T062 [US2] Create asyncpg session factory with tenant context (SET LOCAL "app.tenant_id") in packages/db/src/session.py
- [x] T063 [P] [US2] Create Tenant SQLAlchemy model in packages/db/src/models/tenant.py
- [x] T064 [P] [US2] Create User SQLAlchemy model with role enum in packages/db/src/models/user.py
- [x] T065 [US2] Create Incident SQLAlchemy model with all fields, version column, soft delete, HNSW index in packages/db/src/models/incident.py
- [x] T066 [P] [US2] Create SemgrepRule SQLAlchemy model with category-prefixed ID, revision, approved_by invariant in packages/db/src/models/rule.py
- [x] T067 [P] [US2] Create Finding SQLAlchemy model in packages/db/src/models/finding.py
- [x] T068 [P] [US2] Create Scan SQLAlchemy model with risk_score CHECK constraint in packages/db/src/models/scan.py
- [x] T069 [P] [US2] Create Advisory SQLAlchemy model with nullable file_path/start_line for anchoring in packages/db/src/models/advisory.py
- [x] T070 [P] [US2] Create AuditLogEntry SQLAlchemy model (INSERT only, immutable) in packages/db/src/models/audit_log.py
- [x] T071 [P] [US2] Create SynthesisCandidate SQLAlchemy model with failure_reason, failure_count in packages/db/src/models/synthesis_candidate.py
- [x] T072 [US2] Create initial Alembic migration with all tables, RLS policies, indexes, and CHECK constraints in packages/db/src/migrations/versions/001_initial_schema.py
- [x] T073 [US2] Implement PostgreSQL IncidentRepo adapter (CRUD + optimistic locking + soft/hard delete + linked rule check) in packages/core/src/adapters/pg_incident_repo.py
- [x] T074 [US2] Implement PostgreSQL RuleRepo adapter in packages/core/src/adapters/pg_rule_repo.py
- [x] T075 [US2] Implement Vertex AI Embedding adapter (text-embedding-005, 768 dims) in packages/core/src/adapters/vertex_embedding.py
- [x] T076 [US2] Implement PostgreSQL VectorSearch adapter (cosine distance, HNSW) in packages/core/src/adapters/pg_vector_search.py
- [x] T077 [US2] Implement Incident domain service (create with embedding, update with re-embed, delete with rule check, search) in packages/core/src/domain/incidents/service.py
- [x] T078 [US2] Implement audit log service (record mutations with before/after diffs) in packages/core/src/domain/incidents/audit.py
- [x] T079 [US2] Create seed-knowledge-base.py CLI script (ingest danluu/post-mortems + VOID, --url, --file, --auto-approve, --dry-run) in scripts/seed-knowledge-base.py
- [x] T080 [US2] Create incidents.jsonl seed file with 50+ incidents from public post-mortem databases in scripts/data/incidents.jsonl
- [x] T081 [US2] Create REST API routes for incident CRUD (POST /incidents, GET /incidents, GET /incidents/:id, PUT /incidents/:id, DELETE /incidents/:id) in apps/api/src/routes/incidents.py
- [x] T082 [US2] Create REST API route for URL ingestion (POST /incidents/ingest-url) with LLM extraction draft in apps/api/src/routes/incidents.py
- [x] T083 [US2] Create REST API routes for incident search (GET /incidents?q=&semantic=true) in apps/api/src/routes/incidents.py

**Checkpoint**: PostgreSQL schema deployed, 50+ incidents seeded, CRUD works via API, embedding-based search returns relevant results, audit log records all mutations, optimistic locking rejects concurrent edits.

---

## Phase 5: User Story 3 — RAG Advisory on Pull Requests (Priority: P3)

**Goal**: LLM Router + RAG pipeline + risk classification + advisory generation. Requires Vertex AI.

**Independent Test**: Submit a diff with "retry without backoff", verify risk classification and advisory with matched incident and confidence score.

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T084 [P] [US3] Write unit tests for LLM router (risk score → model selection, fallback chain Flash→Pro→Claude) in packages/core/tests/test_llm_router.py
- [x] T085 [P] [US3] Write unit tests for RAG pipeline (diff → embedding → vector search → advisory generation) in packages/core/tests/test_rag_pipeline.py
- [x] T086 [P] [US3] Write integration test for Vertex AI Gemini Flash adapter in packages/core/tests/integration/test_vertex_gemini_flash.py
- [x] T087 [P] [US3] Write integration test for Vertex AI Gemini Pro adapter in packages/core/tests/integration/test_vertex_gemini_pro.py
- [x] T088 [P] [US3] Write integration test for Vertex AI Claude Sonnet 4 adapter in packages/core/tests/integration/test_vertex_claude.py
- [x] T089 [US3] Write integration test for end-to-end RAG advisory (diff in → advisory comment out) in packages/core/tests/integration/test_rag_e2e.py

### Implementation for User Story 3

- [x] T090 [US3] Implement Vertex AI Gemini Flash LLM adapter in packages/core/src/adapters/vertex_llm.py
- [x] T091 [US3] Implement Vertex AI Gemini Pro LLM adapter (extend vertex_llm.py with model parameter) in packages/core/src/adapters/vertex_llm.py
- [x] T092 [US3] Implement Vertex AI Claude Sonnet 4 adapter (via anthropic[vertex]) in packages/core/src/adapters/vertex_claude.py
- [x] T093 [US3] Implement LLM Router service (risk score → model selection, 30s timeout, fallback chain) in packages/core/src/domain/advisory/llm_router.py
- [x] T094 [US3] Implement RAG pipeline service (extract diff → embed → vector search → build prompt → generate advisory) in packages/core/src/domain/advisory/rag_pipeline.py
- [x] T095 [US3] Implement diff truncation logic (3,000 line limit with warning) in packages/core/src/domain/advisory/diff_processor.py
- [x] T096 [US3] Implement advisory formatting service (structured markdown template with severity badge, incident link, confidence) in packages/core/src/domain/advisory/formatter.py
- [x] T097 [US3] Create RAG worker entry point (Cloud Run Job) in apps/api/src/workers/rag_worker.py
- [x] T098 [US3] Create REST API route for triggering scan with advisory (POST /scans with Layer 2) in apps/api/src/routes/scans.py

**Checkpoint**: RAG pipeline classifies risk in <3s, posts advisory with incident references and confidence scores. LLM router correctly routes Flash/Pro/Claude based on composite score.

---

## Phase 6: User Story 3+1 — GitHub App Integration (Priority: P3 delivery channel)

**Goal**: GitHub App with webhooks, HMAC-SHA256 verification, Check Runs API (L1), PR Reviews API (L2).

**Independent Test**: Install GitHub App on test repo, push anti-pattern → CI fails with SARIF. Open PR → advisory comment posted.

### Tests for User Story 3 (GitHub Channel)

- [x] T099 [P] [US3] Write unit tests for webhook HMAC-SHA256 signature verification in apps/api/tests/unit/test_webhook_auth.py
- [x] T100 [P] [US3] Write unit tests for GitHub webhook event routing (pull_request, push, installation) in apps/api/tests/unit/test_webhook_router.py
- [x] T101 [P] [US3] Write integration test for Check Run creation with SARIF annotations in apps/api/tests/integration/test_check_runs.py
- [x] T102 [US3] Write integration test for PR review comment posting (inline + top-level) in apps/api/tests/integration/test_pr_comments.py

### Implementation for GitHub Channel

- [x] T103 [US3] Implement GitHub adapter (PyGithub: get_pr_diff, create_check_run, post_review_comment, create_pr) in packages/core/src/adapters/github_adapter.py
- [x] T104 [US3] Implement webhook signature verification middleware (HMAC-SHA256, 5min replay protection) in apps/api/src/middleware/webhook_auth.py
- [x] T105 [US3] Implement GitHub webhook routes (pull_request.opened, pull_request.synchronize, push, installation) in apps/api/src/routes/webhooks.py
- [x] T106 [US3] Implement webhook → Layer 1 scan pipeline (fetch diff → run Semgrep → create Check Run with SARIF) in apps/api/src/routes/webhooks.py
- [x] T107 [US3] Implement webhook → Layer 2 advisory pipeline (risk score → LLM route → RAG → post review comment) in apps/api/src/routes/webhooks.py
- [x] T108 [US3] Implement installation.created/deleted handlers (tenant provisioning/deprovisioning) in apps/api/src/routes/webhooks.py

**Checkpoint**: GitHub App receives webhooks, verifies signatures. push events produce SARIF Check Runs. PR events trigger L1+L2 with advisory comments. Installation events provision tenants.

---

## Phase 7: User Story 5 — MCP Server for IDE Integration (Priority: P5)

**Goal**: MCP Server with Streamable HTTP, OAuth 2.1 PKCE, 5 tools, metering.

**Independent Test**: Authenticate via OAuth, call scan_code with anti-pattern, verify response with rule and incident reference.

### Tests for User Story 5

- [x] T109 [P] [US5] Write unit tests for OAuth 2.1 Authorization Code + PKCE flow (authorize, token exchange, refresh, JWT validation) in apps/mcp/tests/test_oauth.py
- [x] T110 [P] [US5] Write unit tests for MCP metering (50 free/month, quota check, quota reset) in apps/mcp/tests/test_metering.py
- [x] T111 [P] [US5] Write unit tests for scan_code tool in apps/mcp/tests/test_tool_scan_code.py
- [x] T112 [P] [US5] Write unit tests for get_incident_advisory tool in apps/mcp/tests/test_tool_advisory.py
- [x] T113 [P] [US5] Write unit tests for list_relevant_incidents tool in apps/mcp/tests/test_tool_list_incidents.py
- [x] T114 [P] [US5] Write unit tests for synthesize_rules tool (Enterprise-only guard) in apps/mcp/tests/test_tool_synthesize.py
- [x] T115 [P] [US5] Write unit tests for validate_fix tool in apps/mcp/tests/test_tool_validate_fix.py

### Implementation for User Story 5

- [x] T116 [US5] Implement OAuth 2.1 provider (authorization endpoint, token endpoint, PKCE verification, RS256 JWT signing) in apps/mcp/src/auth/provider.py
- [x] T117 [US5] Implement OAuth 2.1 auth middleware (JWT validation, tenant/user extraction from claims) in apps/mcp/src/auth/middleware.py
- [x] T118 [US5] Implement MCP metering service (track calls per user per month, check quota, quota reset) in apps/mcp/src/metering.py
- [x] T119 [US5] Implement scan_code MCP tool (run Semgrep on snippet, return findings with incident refs) in apps/mcp/src/tools/scan_code.py
- [x] T120 [US5] Implement get_incident_advisory MCP tool (embed code → vector search → LLM advisory) in apps/mcp/src/tools/get_incident_advisory.py
- [x] T121 [US5] Implement list_relevant_incidents MCP tool (text + semantic search, max_results) in apps/mcp/src/tools/list_relevant_incidents.py
- [x] T122 [US5] Implement synthesize_rules MCP tool (Enterprise guard, create SynthesisCandidate) in apps/mcp/src/tools/synthesize_rules.py
- [x] T123 [US5] Implement validate_fix MCP tool (re-scan fixed code against original rule) in apps/mcp/src/tools/validate_fix.py
- [x] T124 [US5] Create MCP server entry point with Streamable HTTP transport and tool registration in apps/mcp/src/main.py
- [x] T125 [US5] Create MCP server Dockerfile in apps/mcp/Dockerfile

**Checkpoint**: MCP Server authenticates via OAuth 2.1, all 5 tools return correct results, metering enforces 50 free/month quota, Enterprise-only tools guard correctly.

---

## Phase 8: User Story 6 — REST API for Generic CI/CD (Priority: P6)

**Goal**: REST API scan endpoint for GitLab/Bitbucket/Jenkins with API key auth, JSON + SARIF output.

**Independent Test**: Send diff via POST /scans with API key, verify findings in JSON and SARIF formats.

### Tests for User Story 6

- [x] T126 [P] [US6] Write unit tests for API key authentication middleware in apps/api/tests/unit/test_api_key_auth.py
- [x] T127 [P] [US6] Write integration test for POST /scans with diff payload → JSON findings response in apps/api/tests/integration/test_rest_scan.py
- [x] T128 [US6] Write integration test for POST /scans with Accept: application/sarif+json → SARIF response in apps/api/tests/integration/test_rest_sarif.py

### Implementation for User Story 6

- [x] T129 [US6] Implement API key authentication middleware (X-API-Key header, tenant resolution) in apps/api/src/middleware/auth.py
- [x] T130 [US6] Implement SARIF 2.1.0 response formatter in apps/api/src/routes/sarif.py
- [x] T131 [US6] Extend POST /scans route to support API key auth and SARIF content negotiation in apps/api/src/routes/scans.py
- [x] T132 [US6] Implement tier-based feature gating (Free=L1 only, Team=L1+L2) on scan endpoint in apps/api/src/routes/scans.py

**Checkpoint**: REST API accepts diffs via API key, returns findings in JSON and SARIF. Free tier gets L1 only, Team gets L1+L2.

---

## Phase 9: User Story 7 — Dashboard and Configuration Portal (Priority: P7)

**Goal**: SvelteKit dashboard for incidents, rules, scans, team management, billing.

**Independent Test**: Log in as admin, view scan results, toggle a rule, add team member, verify changes.

### Tests for User Story 7

- [ ] T133 [P] [US7] Write unit tests for API client (typed fetch wrappers for incidents, rules, scans, users) in apps/web/tests/unit/api-client.test.ts
- [ ] T134 [P] [US7] Write e2e test for incident CRUD flow (list → create → edit → delete) in apps/web/tests/e2e/incidents.test.ts
- [ ] T135 [P] [US7] Write e2e test for rule management (list rules → toggle enable/disable) in apps/web/tests/e2e/rules.test.ts
- [ ] T136 [US7] Write e2e test for team management (invite user → change role → verify access) in apps/web/tests/e2e/team.test.ts

### Implementation for User Story 7

- [ ] T137 [US7] Create SvelteKit layout with auth guard and navigation in apps/web/src/routes/+layout.svelte
- [ ] T138 [US7] Implement auth pages (login, callback, register) in apps/web/src/routes/auth/
- [ ] T139 [US7] Create typed API client library with auth token management in apps/web/src/lib/api/client.ts
- [ ] T140 [US7] Implement auth and tenant context Svelte stores in apps/web/src/lib/stores/
- [ ] T141 [US7] Implement incidents list page with search (text + semantic) and filters in apps/web/src/routes/(dashboard)/incidents/+page.svelte
- [ ] T142 [US7] Implement incident detail/edit page with form validation and optimistic locking in apps/web/src/routes/(dashboard)/incidents/[id]/+page.svelte
- [ ] T143 [US7] Implement incident ingest-from-URL page (paste URL → review draft → confirm) in apps/web/src/routes/(dashboard)/incidents/ingest/+page.svelte
- [ ] T144 [US7] Implement rules list page with enable/disable toggles and incident links in apps/web/src/routes/(dashboard)/rules/+page.svelte
- [ ] T145 [US7] Implement scan results page with trends chart and findings detail in apps/web/src/routes/(dashboard)/scans/+page.svelte
- [ ] T146 [US7] Implement settings page (tenant config, team members, role management) in apps/web/src/routes/(dashboard)/settings/+page.svelte
- [ ] T147 [US7] Implement billing/usage page with plan limits and upgrade prompts in apps/web/src/routes/(dashboard)/settings/billing/+page.svelte
- [ ] T148 [US7] Implement audit log page (Enterprise only, chronological mutations) in apps/web/src/routes/(dashboard)/audit/+page.svelte
- [ ] T149 [US7] Implement synthesis candidate approval queue page (Enterprise only) in apps/web/src/routes/(dashboard)/rules/candidates/+page.svelte
- [ ] T150 [US7] Create SvelteKit Dockerfile in apps/web/Dockerfile

**Checkpoint**: Dashboard functional for all CRUD flows. Admin can manage incidents, rules, team, and billing. Viewer/editor role restrictions enforced in UI.

---

## Phase 10: Multi-Tenancy, Billing & Tier Enforcement (Priority: P7 continued)

**Goal**: Complete RLS enforcement, tier-based rate limiting, plan limits, billing metering.

**Independent Test**: Create Free-tier tenant, verify 5 contributor limit, 3 repo limit, L1 only. Upgrade to Team, verify L2 access and rate limit change.

### Tests for Multi-Tenancy

- [ ] T151 [P] [US7] Write integration test for RLS tenant isolation (tenant A cannot see tenant B data) in packages/db/tests/integration/test_rls_isolation.py
- [ ] T152 [P] [US7] Write unit tests for rate limiting middleware (per-tier limits, burst allowance) in apps/api/tests/unit/test_rate_limit.py
- [ ] T153 [P] [US7] Write unit tests for plan limit enforcement (contributor/repo caps, layer access) in apps/api/tests/unit/test_plan_limits.py
- [ ] T154 [US7] Write integration test for findings retention auto-purge (Free 90d, Team 1y, Enterprise 2y) in packages/db/tests/integration/test_retention_purge.py

### Implementation for Multi-Tenancy

- [ ] T155 [US7] Implement RLS middleware (extract tenant from JWT/API key, SET LOCAL "app.tenant_id") in apps/api/src/middleware/rls.py
- [ ] T156 [US7] Implement per-tier rate limiting middleware (Free 30/min, Team 120/min, Enterprise 600/min, burst 2x/10s) in apps/api/src/middleware/rate_limit.py
- [ ] T157 [US7] Implement plan limit enforcement service (contributor count, repo count, layer access) in packages/core/src/domain/tenants/plan_limits.py
- [ ] T158 [US7] Implement findings retention scheduled job (auto-purge expired findings per tier) in apps/api/src/workers/retention_purge.py
- [ ] T159 [US7] Create REST API routes for tenant management (GET /tenants/me, users, invite, role update) in apps/api/src/routes/tenants.py
- [ ] T160 [US7] Create REST API route for audit log (GET /audit-log, Enterprise only) in apps/api/src/routes/audit.py
- [ ] T161 [US7] Implement correlation ID middleware for request tracing in apps/api/src/middleware/correlation.py
- [ ] T162 [US7] Configure structlog JSON logging with tenant_id, user_id, correlation_id in apps/api/src/config.py

**Checkpoint**: Tenant isolation verified — no cross-tenant data leaks. Rate limits enforced per tier. Plan limits block excess contributors/repos. Findings auto-purge per retention policy.

---

## Phase 11: User Story 4 — Automatic Rule Synthesis (Priority: P4, Enterprise)

**Goal**: Layer 3 — detect repeated RAG patterns, synthesize Semgrep rules, open PR for review, promote on approval.

**Independent Test**: Simulate 3 advisory matches for same pattern, verify candidate rule PR created with valid YAML and tests, approve and verify promotion to Layer 1.

### Tests for User Story 4

- [ ] T163 [P] [US4] Write unit tests for pattern detection (3+ advisories with same anti_pattern_hash → trigger synthesis) in packages/core/tests/test_synthesis_trigger.py
- [ ] T164 [P] [US4] Write unit tests for rule generation (LLM generates valid Semgrep YAML + test cases) in packages/core/tests/test_rule_generator.py
- [ ] T165 [P] [US4] Write unit tests for SynthesisCandidate lifecycle (pending→approved→promoted, pending→failed→retry, failure_count>=3→archived) in packages/core/tests/test_synthesis_lifecycle.py
- [ ] T166 [US4] Write integration test for end-to-end synthesis pipeline (3 advisories → candidate → PR → approve → L1 rule) in packages/core/tests/integration/test_synthesis_e2e.py

### Implementation for User Story 4

- [ ] T167 [US4] Implement pattern detection service (hash anti-patterns, count advisory matches, trigger at threshold 3) in packages/core/src/domain/rules/pattern_detector.py
- [ ] T168 [US4] Implement rule synthesis service (LLM generates Semgrep YAML + positive/negative test file) in packages/core/src/domain/rules/synthesizer.py
- [ ] T169 [US4] Implement candidate test validator (run semgrep --test on candidate, transition to failed if tests fail) in packages/core/src/domain/rules/test_validator.py
- [ ] T170 [US4] Implement SynthesisCandidate lifecycle service (create, approve→promote, reject, archive, failed→retry with backoff, failure_count check) in packages/core/src/domain/rules/synthesis_service.py
- [ ] T171 [US4] Implement synthesis worker (Cloud Tasks trigger, generate rule, validate tests, open PR) with retry (1min, 5min, 15min) in apps/api/src/workers/synthesis.py
- [ ] T172 [US4] Create REST API routes for synthesis candidates (GET /synthesis/candidates, POST approve, POST reject) in apps/api/src/routes/synthesis.py
- [ ] T173 [US4] Implement auto-archive scheduled job (archive pending candidates older than 30 days, notify admin) in apps/api/src/workers/synthesis_archive.py

**Checkpoint**: Layer 3 detects repeated patterns, generates valid rules with tests, opens PRs. Approval promotes to L1. Failed candidates retry with backoff, auto-archive after 30d or 3 failures. Enterprise-only guard enforced.

---

## Phase 12: Polish & Cross-Cutting Concerns

**Purpose**: Infrastructure, deployment, observability, and production readiness.

- [ ] T174 [P] Create FastAPI Dockerfile (multi-stage build) in apps/api/Dockerfile
- [ ] T175 [P] Create health and readiness probe endpoints in apps/api/src/routes/health.py
- [ ] T176 [P] Create GCP Terraform main configuration (Cloud Run, Cloud SQL, Vertex AI, Secret Manager, Artifact Registry) in infra/gcp/main.tf
- [ ] T177 [P] Create Terraform modules for cloud-run, cloud-sql, vertex-ai, secret-manager, artifact-registry, iam in infra/gcp/modules/
- [ ] T178 [P] Create Terraform environment tfvars (dev, staging, prod) in infra/gcp/environments/
- [ ] T179 [P] Create Terraform IAM module for Workload Identity Federation (GitHub Actions → GCP) in infra/gcp/modules/iam/
- [ ] T180 Create GitHub Actions deploy workflow (build → push to Artifact Registry → deploy to Cloud Run) in .github/workflows/deploy.yml
- [ ] T181 [P] Configure OpenTelemetry tracing (spans: API→LLM→DB) with GCP Cloud Trace exporter in apps/api/src/config.py
- [ ] T182 [P] Configure Cloud Monitoring custom metrics (LLM latency per model, rule match rates, tenant usage) in packages/core/src/domain/observability/metrics.py
- [ ] T183 [P] Write tests for false positive reporting endpoint (POST /findings/:id/false-positive returns 200, updates finding status, increments false_positive_count, auto-disables at threshold 3, requires editor+ role) in apps/api/tests/test_findings.py
- [ ] T184 [P] Create false positive reporting endpoint (POST /findings/:id/false-positive, auto-disable at threshold 3) in apps/api/src/routes/findings.py
- [ ] T185 [P] Create sync-rules.py script for syncing rules to GitHub App / API consumers in scripts/sync-rules.py
- [ ] T186 [P] Create .dependabot.yml for automated dependency updates in .github/dependabot.yml
- [ ] T187 Run quickstart.md validation scenarios (all 8 scenarios) as acceptance tests
- [ ] T188 Verify 80% unit test coverage across all packages (pytest --cov)
- [ ] T189 Run full Semgrep rule test suite and verify all 10+ rules pass

**Checkpoint**: Terraform plan dry-run passes without errors. Docker builds for all apps complete without warnings. OpenTelemetry traces arrive in Cloud Monitoring on staging. GitHub Actions full workflow green (lint + test + build + deploy). Semgrep scan of oute-muscle codebase itself passes with zero critical findings.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1
- **Phase 3 (US1 — Semgrep Rules)**: Depends on Phase 2 — delivers Layer 1 MVP
- **Phase 4 (US2 — Knowledge Base)**: Depends on Phase 2 — first GCP dependency (Cloud SQL, Vertex AI embeddings)
- **Phase 5 (US3 — RAG Advisory)**: Depends on Phase 4 (needs incidents in DB) — adds Vertex AI LLM
- **Phase 6 (GitHub App)**: Depends on Phase 3 (L1 rules) + Phase 5 (L2 advisory)
- **Phase 7 (US5 — MCP Server)**: Depends on Phase 3 (L1 scan) + Phase 4 (incidents for advisory)
- **Phase 8 (US6 — REST API)**: Depends on Phase 3 (L1 scan) + Phase 5 (L2 advisory)
- **Phase 9 (US7 — Dashboard)**: Depends on Phase 4 (incident CRUD API) + Phase 8 (REST API)
- **Phase 10 (Multi-Tenancy)**: Depends on Phase 4 (DB schema) — can start after Phase 4, apply incrementally
- **Phase 11 (US4 — Synthesis)**: Depends on Phase 5 (RAG) + Phase 6 (GitHub PR creation) — Layer 3, last
- **Phase 12 (Polish)**: Depends on all prior phases — production readiness

### User Story Dependencies

- **US1 (P1)**: After Foundational — no dependencies on other stories
- **US2 (P2)**: After Foundational — no dependencies on other stories
- **US3 (P3)**: After US2 (needs knowledge base for RAG)
- **US4 (P4)**: After US3 (needs RAG) + GitHub adapter (needs PR creation) — Enterprise only
- **US5 (P5)**: After US1 (scan_code needs rules) + US2 (advisory needs incidents)
- **US6 (P6)**: After US1 (L1 scan) + US3 (L2 advisory)
- **US7 (P7)**: After US2 (incident API) + US6 (REST API)

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- Phase 3 (US1) and Phase 4 (US2) can run in parallel after Foundational
- Phase 7 (MCP) and Phase 8 (REST API) can run in parallel after Phase 5
- All [P] tasks within a phase can run in parallel
- Different user stories on separate branches by different developers

---

## Parallel Example: Phase 3 (User Story 1)

```bash
# Launch all rule tests in parallel:
Task: T028-T037 — All 10 rule test files (different categories, no deps)

# Launch all rule implementations in parallel:
Task: T039-T048 — All 10 rule YAML files (different categories, no deps)
```

## Parallel Example: Phase 4 (User Story 2)

```bash
# Launch all model definitions in parallel:
Task: T063-T071 — All SQLAlchemy models (different files, no deps)

# Launch test definitions in parallel:
Task: T055-T059 — All unit/integration tests (different test files)
```

---

## Implementation Strategy

### MVP First (Phase 1-3: Layer 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational domain entities and ports
3. Complete Phase 3: 10 Semgrep rules + pre-commit + GitHub Action
4. **STOP and VALIDATE**: Run all rule tests, verify pre-commit <2s, verify SARIF in Security Tab
5. Deploy/demo if ready — Layer 1 delivers value with zero GCP infrastructure

### Incremental Delivery

1. Phase 1-3 → Layer 1 MVP (no GCP)
2. Phase 4 → Knowledge Base (first GCP: Cloud SQL + Vertex AI embeddings)
3. Phase 5-6 → Layer 2 RAG + GitHub App (full L1+L2 pipeline)
4. Phase 7-8 → MCP Server + REST API (all 3 delivery channels)
5. Phase 9-10 → Dashboard + Multi-tenancy (operational management)
6. Phase 11 → Layer 3 Synthesis (Enterprise, only after L2 proven)
7. Phase 12 → Polish, observability, deployment automation

### Parallel Team Strategy

With multiple developers:

1. Team completes Phase 1-2 together
2. Once Foundational is done:
   - Developer A: Phase 3 (Semgrep rules — L1 MVP)
   - Developer B: Phase 4 (Knowledge Base — DB + CRUD)
3. After Phase 3+4:
   - Developer A: Phase 5 (RAG + LLM Router)
   - Developer B: Phase 7 (MCP Server)
4. Continue in parallel until all phases complete

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each phase is independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate phase independently
- Layer 1 (Phase 3) has ZERO GCP dependency — ships as standalone Semgrep rules
- Layer 2 requires Vertex AI (Phase 5+) — first GCP dependency
- Layer 3 (Phase 11) builds only after Layer 2 is proven — Constitution Principle XI
