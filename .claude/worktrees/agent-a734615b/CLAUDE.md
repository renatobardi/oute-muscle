# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Oute Muscle** is an incident-based code guardrails platform that prevents production incidents from recurring in code. It bridges post-mortem documentation to detection rules via 3 layers: static Semgrep rules (blocking), RAG advisory (consultive), and automatic rule synthesis (progressive).

## Constitution

Ratified at `.specify/memory/constitution.md` (v1.1.0, 12 principles). Key principles:

- **Incident Traceability**: Every rule links to a real documented incident
- **Three-Layer Detection**: L1 Semgrep (blocking) → L2 RAG (consultive) → L3 Synthesis (progressive)
- **Hexagonal Boundaries**: Ports/adapters only at real boundaries (LLM router, delivery channels, GCP adapters)
- **Incremental Complexity**: L1 proven before L2, L2 before L3. Abstractions require 2 implementations
- **Quality Gates**: TDD mandatory, 80% coverage, mypy strict, Ruff, ESLint

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI (Python 3.12+), asyncpg, pydantic v2, uvicorn |
| Frontend | SvelteKit, TypeScript strict, Tailwind CSS, shadcn-svelte |
| Database | PostgreSQL 16 + pgvector (Cloud SQL), HNSW indexes, RLS |
| LLM | Vertex AI (Gemini 2.5 Flash/Pro + Claude Sonnet 4), text-embedding-005 |
| Static Analysis | Semgrep (custom rules with mandatory test files) |
| Infra | GCP Managed: Cloud Run, Cloud SQL, Vertex AI, Secret Manager |
| CI/CD | GitHub Actions, Workload Identity Federation, Conventional Commits |
| Testing | pytest + pytest-asyncio (backend), vitest + playwright (frontend) |
| Linting | Ruff (Python), ESLint + eslint-plugin-svelte (frontend) |

## Monorepo Structure

```
apps/api/          — FastAPI backend (API + workers)
apps/web/          — SvelteKit dashboard
apps/mcp/          — MCP Server (Streamable HTTP + OAuth 2.1)
packages/core/     — Shared domain logic (hexagonal: domain/, ports/, adapters/)
packages/db/       — SQLAlchemy models + Alembic migrations
packages/semgrep-rules/ — Rules organized by 10 categories
infra/gcp/         — Terraform (Cloud Run, Cloud SQL, Vertex AI, IAM)
scripts/           — CLI tools (seeding, rule sync)
.github/workflows/ — CI, deploy, Semgrep scan
```

## Current Feature: 001-incident-code-guardrails

**Branch**: `001-incident-code-guardrails`
**Status**: Design complete, ready for implementation

### Design Artifacts (specs/001-incident-code-guardrails/)

| Artifact | Content |
|----------|---------|
| spec.md | 7 user stories (P1-P7), 32 functional requirements, 10 success criteria |
| plan.md | Tech stack, monorepo structure, constitution check (12/12 PASS) |
| data-model.md | 9 entities: Tenant, User, Incident, SemgrepRule, Scan, Finding, Advisory, AuditLogEntry, SynthesisCandidate |
| research.md | 8 research decisions (Semgrep SARIF, pgvector HNSW, Vertex AI routing, GitHub App, MCP OAuth, RLS, monorepo, observability) |
| contracts/ | 4 contracts: api-rest.md, api-github-webhook.md, api-mcp-tools.md, api-internal.md |
| tasks.md | 189 tasks across 12 phases |

### Findings Resolved

13 findings (F1-F13) from two analyze cycles, all resolved:
- F1-F10: spec/data-model/contract consistency (rate limits, pagination, versioning, locking, etc.)
- F11: Phase 12 checkpoint added
- F12: TDD test for false positive endpoint added
- F13: FastAPI entry point moved to Phase 4

### Implementation Phases

| Phase | Scope | Tasks |
|-------|-------|-------|
| 1 | Setup (monorepo init) | T001-T012 |
| 2 | Foundational (domain + ports) | T013-T027 |
| 3 | **US1 — Semgrep Rules (L1 MVP, zero GCP)** | T028-T053 |
| 4 | US2 — Knowledge Base (PostgreSQL + CRUD) | T054-T083 |
| 5 | US3 — RAG Advisory (LLM Router) | T084-T098 |
| 6 | GitHub App (webhooks + Check Runs) | T099-T108 |
| 7 | US5 — MCP Server (5 tools + OAuth) | T109-T125 |
| 8 | US6 — REST API (SARIF + API key) | T126-T132 |
| 9 | US7 — Dashboard (SvelteKit) | T133-T150 |
| 10 | Multi-tenancy (RLS + billing + tiers) | T151-T162 |
| 11 | US4 — Synthesis (L3, Enterprise) | T163-T173 |
| 12 | Polish (infra, deploy, observability) | T174-T189 |

### Next Steps

1. `/speckit.taskstoissues` — Convert tasks to GitHub issues
2. `/speckit.implement` — Start with Phase 1 (Setup)

## SpecKit Workflow

This project uses SpecKit v0.4.3 for structured feature development:

1. `/speckit.constitution` → `/speckit.specify` → `/speckit.clarify` → `/speckit.plan` → `/speckit.tasks` → `/speckit.analyze` → `/speckit.implement`

## Key Scripts

All in `.specify/scripts/bash/`:

- `create-new-feature.sh` — Creates feature branch + spec directory. Flags: `--json`, `--short-name`, `--timestamp`
- `check-prerequisites.sh` — Validates feature context. Flags: `--json`, `--require-tasks`, `--include-tasks`, `--paths-only`

## Branch Naming

Sequential numbering (`NNN-short-name`), configured in `.specify/init-options.json`. Auto-increments by scanning branches and `specs/`.

## Conventions

- Tasks format: `- [ ] TXXX [P] [USY] Description with file path`
- Commits: Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`)
- Code + public docs: English. Internal docs: PT-BR
- Semgrep rule IDs: `{category}-{NNN}` (e.g., `unsafe-regex-001`)
