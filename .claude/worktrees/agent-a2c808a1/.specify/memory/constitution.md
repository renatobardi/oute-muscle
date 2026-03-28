<!--
  Sync Impact Report
  ==================
  Version change: 1.0.0 → 1.1.0 (MINOR — principle rewording/refinement)

  Modified principles:
    X.  Clean Code & Hexagonal Architecture → Clean Architecture & Hexagonal Boundaries
        (scoped hexagonal to real domain boundaries only; banned speculative interfaces)
    XI. Simplicity / YAGNI → Incremental Complexity
        (added layer-gating rule: L1 proven before L2, L2 before L3;
         explicit "two implementations to justify abstraction" rule)

  Templates requiring updates:
    - .specify/templates/plan-template.md         — ✅ no update needed
    - .specify/templates/spec-template.md          — ✅ no update needed
    - .specify/templates/tasks-template.md         — ✅ no update needed

  Follow-up TODOs: none
-->

# Oute Muscle Constitution

## Core Principles

### I. Product Mission

Oute Muscle exists to PREVENT production incidents from recurring in code.
The product bridges post-mortem documentation and code detection rules — no
competitor does this. Every feature MUST demonstrably serve this mission or
be rejected.

### II. Incident Traceability

Every detection rule MUST be traceable to a real, documented incident
(traceability chain). Rules without a linked incident are invalid and MUST
NOT be merged. The chain is: Incident Report → Knowledge Base Entry →
Detection Rule → Test Cases.

### III. Three-Layer Detection

The system operates in three layers with distinct guarantees:

- **Layer 1 — Static Rules (Semgrep)**: Blocking. Runs in pre-commit hooks
  and GitHub Actions. A match MUST fail the check.
- **Layer 2 — RAG Advisory**: Consultive. Uses vector similarity to surface
  relevant past incidents for human review. MUST NOT block merges.
- **Layer 3 — Automatic Rule Synthesis**: Progressive. LLM-generated rules
  from new incidents. MUST pass human review before promotion to Layer 1.

### IV. Architecture & Infrastructure

- Deploy EXCLUSIVELY on GCP Managed Services: Cloud Run, Cloud SQL,
  Vertex AI. No self-managed VMs or Kubernetes.
- Database: PostgreSQL with pgvector on Cloud SQL.
- API: FastAPI (Python).
- Frontend: SvelteKit (dashboard, configuration portal).
- Embeddings: Vertex AI text-embedding-005.
- Multi-tenancy: Row-Level Security (RLS) on PostgreSQL with pgvector
  partitioned by tenant.

### V. Hybrid LLM Strategy

All LLM access is via a single Vertex AI account with unified IAM, billing,
and monitoring:

| Model | Use Case | Traffic Share |
|-------|----------|---------------|
| Gemini 2.5 Flash | Fast triage of standard PRs | ~70% |
| Gemini 2.5 Pro | Medium-complexity analysis | ~15% |
| Claude Sonnet 4 | Deep analysis of high-risk PRs | ~15% |

Model routing is deterministic based on risk score, not random. Fallback
order: Flash → Pro → Claude Sonnet 4.

### VI. Data Privacy & Multi-Tenancy

- NEVER store customer source code at rest — only findings metadata.
- Tenant isolation via PostgreSQL RLS. Every query MUST include tenant
  context; queries without tenant filtering MUST fail at the ORM layer.
- pgvector indexes MUST be partitioned by tenant.

### VII. Quality Gates

- Every Semgrep rule MUST have an associated test file with positive and
  negative test cases.
- Minimum unit test coverage: 80%.
- Integration tests are MANDATORY for: incident ingestion, pgvector
  similarity search, and rule generation via LLM.
- TDD (Test-First) is the default workflow: tests written → tests fail →
  implement → tests pass → refactor.
- Linting: Ruff (Python), ESLint + eslint-plugin-svelte (SvelteKit).
- Type checking: mypy strict mode (Python), TypeScript strict (SvelteKit).

### VIII. Security Posture

- Credentials for LLM and DB EXCLUSIVELY in GCP Secret Manager — zero
  environment variables with secrets.
- Workload Identity Federation for GitHub Actions (GCP) — zero service
  account keys.
- Vertex AI IAM: no external API keys for Gemini or Claude —
  authentication via service account only.
- Webhook authentication via shared secret (HMAC-SHA256) for GitHub
  integration.
- Rate limiting on ALL public endpoints.
- SOC 2 readiness as a design goal from day one.

### IX. Delivery Channels & Open-Core

The product is delivered via three channels:

1. **GitHub App** — primary integration point.
2. **MCP Server** (Streamable HTTP + OAuth 2.1) — IDE and agent integration.
3. **REST API** — programmatic access.

Open-core model:

- Public rules (50-100) are open-source.
- Full knowledge base and rule synthesis are commercial.

Pricing tiers:

| Tier | Price | Limits | Layers |
|------|-------|--------|--------|
| Free | $0 | 5 contributors, 3 repos | L1 |
| Team | $29/contributor/month | Unlimited | L1 + L2 |
| Enterprise | $18K+/year | Custom | L1 + L2 + L3 |

Layer 1 pre-commit hook and GitHub Action MUST be identical regardless of
delivery channel.

### X. Clean Architecture & Hexagonal Boundaries

- Apply hexagonal architecture (ports & adapters) at real domain boundaries
  only: LLM router (multiple providers), delivery channels (GitHub App,
  MCP Server, REST API), and GCP infrastructure adapters (Cloud SQL,
  Vertex AI, Secret Manager).
- Do NOT create interfaces where only one implementation exists today and
  no second implementation is planned.
- Dependency injection is mandatory at these boundaries.
- Domain logic MUST be framework-agnostic and independently testable
  without GCP credentials.

### XI. Incremental Complexity

- Build what today's validated use case requires.
- Layer 1 MUST be proven before Layer 2 exists. Layer 2 MUST be proven
  before Layer 3 exists. No Enterprise feature before the first Enterprise
  customer.
- In code: abstractions require two concrete implementations to justify
  creation. When in doubt, duplicate once, abstract on the second
  repetition.

### XII. Observability

- Structured logging (JSON) in all services from day one.
- Request tracing with correlation IDs across API → LLM → DB calls.
- Metrics for: LLM latency per model, rule match rates, tenant usage,
  vector search performance.
- All observability via GCP-native tooling (Cloud Logging, Cloud Trace,
  Cloud Monitoring).

## Technology Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| API | FastAPI (Python) | Async, strict mypy |
| Frontend | SvelteKit | TypeScript strict, ESLint + Svelte plugin |
| Database | PostgreSQL + pgvector (Cloud SQL) | RLS for multi-tenancy |
| LLM | Vertex AI (Gemini Flash/Pro, Claude Sonnet 4) | Single account, IAM auth |
| Embeddings | Vertex AI text-embedding-005 | $0.10/MTok |
| Static Analysis | Semgrep | Custom rules with mandatory tests |
| Infra | GCP Managed (Cloud Run, Cloud SQL, Vertex AI) | No VMs, no K8s |
| Python Linting | Ruff | Replaces flake8, isort, black |
| Frontend Linting | ESLint + eslint-plugin-svelte | With Prettier |
| CI/CD | GitHub Actions | Workload Identity Federation |

## Communication & Standards

- Internal documentation: PT-BR.
- Public documentation and all code: English.
- Code comments: English.
- Commits: Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, etc.).
- Public README: English, with "Built with Claude" section.

## Governance

- This constitution supersedes all other practices. When in conflict,
  the constitution wins.
- All PRs MUST verify compliance with applicable principles before merge.
- Amendments require: (1) documented rationale, (2) review approval,
  (3) migration plan for existing code if breaking.
- Version follows semantic versioning: MAJOR for principle
  removals/redefinitions, MINOR for additions/expansions, PATCH for
  clarifications.
- Complexity beyond what the constitution allows MUST be justified in
  the plan's Complexity Tracking table with: violation, why needed, and
  simpler alternative rejected.

**Version**: 1.1.0 | **Ratified**: 2026-03-28 | **Last Amended**: 2026-03-28
