# Implementation Plan: Admin Cockpit, Firebase Auth & Custom Domain

**Branch**: `237-admin-auth-domain` | **Date**: 2026-03-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/237-admin-auth-domain/spec.md`

## Summary

Replace custom OAuth 2.1 authentication with Firebase Auth (shared project `oute-488706` with oute.me), configure `muscle.oute.pro` custom domain on Cloud Run, and build a comprehensive admin cockpit at `/admin` for platform operations. SvelteKit handles Firebase session cookies as BFF; FastAPI API stays Firebase-free (existing JWT/API-key auth preserved for external consumers).

## Technical Context

**Language/Version**: Python 3.12+ (API), TypeScript strict (Web, SvelteKit)
**Primary Dependencies**: firebase (client SDK), firebase-admin (server SDK), @sveltejs/adapter-node
**Storage**: PostgreSQL 16 + pgvector (Cloud SQL) — existing
**Testing**: pytest (API), vitest + playwright (Web)
**Target Platform**: GCP Cloud Run (API + Web + MCP)
**Project Type**: Multi-service web platform
**Performance Goals**: Login <5s, Admin cockpit load <3s, Admin search <2s, Metrics refresh 60s
**Constraints**: Session cookie 5-day max, ADMIN_EMAILS env var for admin bootstrap, DNS managed externally
**Scale/Scope**: 100 tenants, 150 users, 6 admin cockpit sections, 7 admin API endpoints

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Product Mission | PASS | Admin cockpit enables platform operations; auth enables user access |
| II. Incident Traceability | N/A | Feature does not create/modify detection rules |
| III. Three-Layer Detection | N/A | Feature does not modify detection layers |
| IV. Architecture & Infrastructure | PASS | GCP Cloud Run domain mapping, Cloud SQL, SvelteKit, FastAPI |
| V. Hybrid LLM Strategy | N/A | No LLM usage in this feature |
| VI. Data Privacy & Multi-Tenancy | PASS | Admin bypasses RLS intentionally (cross-tenant read); mutations audit-logged |
| VII. Quality Gates | PASS | TDD, tests for auth flow + admin endpoints + domain verification |
| VIII. Security Posture | PASS | Firebase session cookies (httpOnly, secure), CORS restricted, admin role enforcement |
| IX. Delivery Channels & Open-Core | PASS | Web dashboard delivery channel enhanced |
| X. Clean Architecture & Hexagonal | PASS | No new abstract interfaces; Firebase is a concrete adapter at a real boundary |
| XI. Incremental Complexity | PASS | Firebase patterns proven in oute.me; admin cockpit uses existing data models |
| XII. Observability | PASS | Admin actions audit-logged; existing structured logging applies |

**Gate result**: ALL PASS — proceed.

## Project Structure

### Documentation (this feature)

```text
specs/237-admin-auth-domain/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── api-admin.md     # Admin API contract
│   └── api-auth.md      # Auth session contract
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (changes to existing monorepo)

```text
apps/web/                            # SvelteKit — Firebase Auth + Admin Cockpit
├── src/
│   ├── lib/
│   │   ├── firebase.ts              # NEW: Firebase client SDK singleton
│   │   ├── server/
│   │   │   ├── firebase-admin.ts    # NEW: Firebase Admin SDK singleton
│   │   │   ├── auth.ts             # NEW: verifyAuthToken (cookie + bearer)
│   │   │   └── users.ts            # NEW: getOrCreateUser (JIT provisioning via FastAPI API)
│   │   ├── api/
│   │   │   ├── client.ts           # MODIFY: add admin namespace
│   │   │   └── index.ts            # MODIFY: update base URL config
│   │   └── stores/
│   │       └── auth.ts             # MODIFY: replace OAuth with Firebase state
│   ├── routes/
│   │   ├── auth/
│   │   │   ├── login/+page.svelte  # REWRITE: Firebase email + Google sign-in
│   │   │   └── callback/           # DELETE: no more OAuth callback
│   │   ├── pending/+page.svelte    # NEW: pending approval landing page
│   │   ├── api/auth/
│   │   │   └── session/+server.ts  # NEW: POST/DELETE session exchange
│   │   ├── admin/
│   │   │   ├── +layout.svelte      # NEW: admin layout with sidebar nav
│   │   │   ├── +layout.server.ts   # NEW: admin role guard (server-side)
│   │   │   ├── +page.svelte        # NEW: admin dashboard overview
│   │   │   ├── users/+page.svelte  # NEW: user management
│   │   │   ├── tenants/+page.svelte # NEW: tenant management
│   │   │   ├── health/+page.svelte # NEW: platform health metrics
│   │   │   ├── incidents/+page.svelte # NEW: incident KB metrics
│   │   │   ├── rules/+page.svelte  # NEW: rule metrics + synthesis approval
│   │   │   └── access/+page.svelte # NEW: audit log + access control
│   │   └── +layout.server.ts       # NEW: root auth via hooks
│   ├── hooks.server.ts             # NEW: authenticate + gateUser sequence
│   └── +layout.svelte              # MODIFY: use server-side auth data
├── package.json                     # MODIFY: add firebase, firebase-admin, adapter-node
└── svelte.config.js                 # MODIFY: switch to adapter-node

apps/api/                            # FastAPI — Admin API Endpoints
├── src/
│   ├── routes/
│   │   └── admin.py                # NEW: /v1/admin/* endpoints (7 endpoints)
│   ├── middleware/
│   │   ├── auth.py                 # MODIFY: add require_admin dependency
│   │   └── rls.py                  # MODIFY: admin bypass (no SET LOCAL)
│   └── main.py                     # MODIFY: register admin router, update CORS
├── tests/
│   ├── unit/
│   │   └── test_admin_routes.py    # NEW: admin endpoint tests
│   └── integration/
│       └── test_admin_api.py       # NEW: admin cross-tenant query tests

packages/db/
├── src/
│   ├── models/
│   │   └── user.py                 # MODIFY: add firebase_uid, display_name, email_verified, last_login
│   └── migrations/versions/
│       └── 004_firebase_auth_fields.py  # NEW: migration for User model changes

infra/gcp/
├── modules/cloud-run/
│   └── main.tf                     # MODIFY: add domain mapping resource
└── main.tf                         # MODIFY: pass domain vars to cloud-run module

.github/workflows/
└── deploy.yml                      # MODIFY: deploy web service, add domain verification step
```

**Structure Decision**: No new apps or packages. All changes extend existing apps/web (Firebase + admin cockpit), apps/api (admin endpoints), packages/db (User model), and infra/gcp (domain mapping). This minimizes blast radius and reuses all existing patterns.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Admin RLS bypass | Admin needs cross-tenant reads for cockpit | Superuser RLS policy adds security surface; simpler to skip SET LOCAL |
| Firebase SDK in SvelteKit only | BFF pattern: SvelteKit handles Firebase, API stays Firebase-free | Adding Firebase Admin SDK to Python API duplicates verification and adds dependency |
| Second Cloud Run service (web) | Web needs Node.js runtime for SSR + session cookies | Same service as API would require different runtimes (Python vs Node) |
