# Tasks: Admin Cockpit, Firebase Auth & Custom Domain

**Input**: Design documents from `/specs/237-admin-auth-domain/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: TDD approach — test tasks precede implementation per Constitution Principle VII.

**Organization**: Tasks grouped by user story (P1→P4) to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Backend API**: `apps/api/src/`, `apps/api/tests/`
- **Frontend**: `apps/web/src/`, `apps/web/tests/`
- **Database**: `packages/db/src/`, `packages/db/tests/`
- **Infrastructure**: `infra/gcp/`
- **CI/CD**: `.github/workflows/`

---

## Phase 1: Setup

**Purpose**: Install dependencies, configure Firebase SDKs, update SvelteKit adapter.

- [x] T001 Install firebase, firebase-admin, and @sveltejs/adapter-node; remove @sveltejs/adapter-auto in apps/web/package.json
- [x] T002 Switch SvelteKit adapter to adapter-node in apps/web/svelte.config.js
- [x] T003 [P] Add Firebase environment variables to apps/web/.env.example (PUBLIC_FIREBASE_API_KEY, PUBLIC_FIREBASE_AUTH_DOMAIN, PUBLIC_FIREBASE_PROJECT_ID, PUBLIC_FIREBASE_APP_ID, FIREBASE_PROJECT_ID, FIREBASE_CLIENT_EMAIL, FIREBASE_PRIVATE_KEY)
- [x] T004 [P] Add ADMIN_EMAILS and ALLOWED_ORIGINS environment variables to apps/api/src/config.py

**Checkpoint**: Dependencies installed, adapter switched, env vars documented.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: User model migration, Firebase SDK singletons, auth verification — blocks all user stories.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T005 Add firebase_uid (String, unique, indexed), display_name (String, nullable), email_verified (Boolean, default false), last_login (DateTime, nullable) columns to User model in packages/db/src/models/user.py
- [x] T006 Create Alembic migration 004_firebase_auth_fields.py in packages/db/src/migrations/versions/004_firebase_auth_fields.py
- [x] T007 Create Firebase client SDK singleton in apps/web/src/lib/firebase.ts (initializeApp, getAuth, GoogleAuthProvider export)
- [x] T008 [P] Create Firebase Admin SDK singleton in apps/web/src/lib/server/firebase-admin.ts (ADC for Cloud Run, cert for local dev)
- [x] T009 Create server-side auth verification module in apps/web/src/lib/server/auth.ts (verifyAuthToken supporting __session cookie + Bearer token)
- [x] T010 Create SvelteKit hooks.server.ts in apps/web/src/hooks.server.ts (authenticate + gateUser sequence handler)
- [x] T011 Create root +layout.server.ts in apps/web/src/routes/+layout.server.ts (load user from auth hook, pass to layout)
- [x] T012 Update +layout.svelte in apps/web/src/routes/+layout.svelte (use server-side auth data instead of client-side store, remove old OAuth guard)

**Checkpoint**: Firebase SDK initialized, auth hooks work, User model has firebase_uid. Server-side auth guards all routes.

---

## Phase 3: User Story 1 — Firebase Authentication (Priority: P1) 🎯 MVP

**Goal**: Users sign in via email/password or Google, session cookie created, JIT user provisioning.

**Independent Test**: Navigate to /auth/login, sign in with Google, verify session cookie set and dashboard loads.

### Tests for User Story 1

- [x] T013 [P] [US1] Write unit test for session exchange endpoint (POST /api/auth/session with valid/invalid idToken) in apps/web/tests/unit/auth-session.test.ts
- [x] T014 [P] [US1] Write unit test for JIT user provisioning (first login creates user record with viewer role) in apps/web/tests/unit/user-sync.test.ts

### Implementation for User Story 1

- [x] T015 [US1] Create session exchange endpoint POST /api/auth/session in apps/web/src/routes/api/auth/session/+server.ts (verify idToken, create session cookie, sync user to DB via FastAPI API call)
- [x] T016 [US1] Create logout endpoint DELETE /api/auth/session in apps/web/src/routes/api/auth/session/+server.ts (revoke tokens, delete cookie)
- [x] T017 [US1] Create getOrCreateUser function in apps/web/src/lib/server/users.ts (calls FastAPI POST /v1/tenants/register or internal user endpoint to lookup/create by firebase_uid, update last_login, check ADMIN_EMAILS for admin role)
- [x] T018 [US1] Rewrite login page with Firebase email/password + Google sign-in in apps/web/src/routes/auth/login/+page.svelte
- [x] T019 [US1] Create pending approval landing page in apps/web/src/routes/pending/+page.svelte (shown to users with no tenant)
- [x] T020 [US1] Delete OAuth callback route apps/web/src/routes/auth/callback/ (no longer needed)
- [x] T021 [US1] Update auth store in apps/web/src/lib/stores/auth.ts (replace OAuth token logic with Firebase auth state, onAuthStateChanged)
- [x] T022 [US1] Update gateUser in hooks.server.ts to redirect tenant-less users to /pending in apps/web/src/hooks.server.ts

**Checkpoint**: Users can sign in via email or Google. Session cookie set. JIT provisioning creates user in DB via API. Tenant-less users see pending page.

---

## Phase 4: User Story 2 — Custom Domain (Priority: P2)

**Goal**: muscle.oute.pro serves web app via SvelteKit Cloud Run service. SvelteKit proxies /api/* requests to the FastAPI Cloud Run service (BFF pattern). mcp.muscle.oute.pro serves MCP. CORS restricted.

**Independent Test**: Navigate to https://muscle.oute.pro, verify TLS certificate and page loads. Call /api/v1/health, verify 200.

### Implementation for User Story 2

- [x] T023 [US2] Add google_cloud_run_domain_mapping resource for muscle.oute.pro in infra/gcp/modules/cloud-run/main.tf
- [x] T024 [US2] Add domain mapping variable and output in infra/gcp/modules/cloud-run/main.tf (custom_domains list variable, verified_domain_mappings output)
- [x] T025 [US2] Pass domain mapping config from infra/gcp/main.tf to cloud-run module (muscle.oute.pro for web+api, mcp.muscle.oute.pro for MCP)
- [x] T026 [US2] Replace CORS wildcard with explicit allowed origins in apps/api/src/main.py (use ALLOWED_ORIGINS from config: muscle.oute.pro, oute.pro, localhost)
- [x] T027 [US2] Update API base URL in apps/web/src/lib/api/index.ts (default to https://muscle.oute.pro/api/v1)
- [x] T028 [US2] Add web service deployment to .github/workflows/deploy.yml (build + push apps/web Docker image, deploy to Cloud Run)
- [x] T029 [US2] Update apps/web/Dockerfile to use adapter-node build output with firebase-admin dependency (node build, EXPOSE 3000)

**Checkpoint**: Custom domain serves web and API with valid TLS. CORS restricted. Deploy pipeline deploys both services.

---

## Phase 5: User Story 4 — Admin API Endpoints (Priority: P4)

**Goal**: FastAPI admin endpoints at /v1/admin/ with cross-tenant reads and audit-logged mutations.

**Note**: Phase 5 (Admin API) runs BEFORE Phase 6 (Admin Cockpit UI) because the cockpit depends on these endpoints.

**Independent Test**: Authenticate as admin, call GET /v1/admin/users, verify cross-tenant user list.

### Tests for User Story 4

- [x] T030 [P] [US4] Write unit tests for admin route auth guard (admin gets 200, non-admin gets 403) in apps/api/tests/unit/test_admin_routes.py
- [x] T031 [P] [US4] Write unit tests for admin user management (role change, self-demotion block, deactivate, activate, assign tenant) in apps/api/tests/unit/test_admin_users.py
- [x] T032 [P] [US4] Write integration test for admin cross-tenant queries (users from multiple tenants returned) in apps/api/tests/integration/test_admin_api.py

### Implementation for User Story 4

- [x] T033 [US4] Create require_admin dependency in apps/api/src/middleware/auth.py (checks request.state.role == "admin", returns 403 otherwise)
- [x] T034 [US4] Add admin RLS bypass to apps/api/src/middleware/rls.py (skip SET LOCAL for admin requests, add is_admin flag to request.state)
- [x] T035 [US4] Create admin routes file in apps/api/src/routes/admin.py with: GET /admin/users (paginated, searchable, cross-tenant)
- [x] T036 [US4] Add GET /admin/tenants endpoint in apps/api/src/routes/admin.py (with contributor_count, scan_count_30d aggregations)
- [x] T037 [US4] Add GET /admin/metrics endpoint in apps/api/src/routes/admin.py (aggregated counts: users, tenants, scans, findings, incidents, rules, LLM usage; plus p50/p95 latency from OpenTelemetry metrics export)
- [x] T038 [US4] Add POST /admin/users/{id}/role endpoint in apps/api/src/routes/admin.py (change role, block self-demotion, audit log)
- [x] T039 [US4] Add POST /admin/users/{id}/deactivate and POST /admin/users/{id}/activate endpoints in apps/api/src/routes/admin.py (toggle is_active, audit log)
- [x] T040 [US4] Add POST /admin/users/{id}/assign-tenant endpoint in apps/api/src/routes/admin.py (set tenant_id, audit log)
- [x] T041 [US4] Add GET /admin/audit-log endpoint in apps/api/src/routes/admin.py (cross-tenant, filterable by entity_type, action, date range)
- [x] T042 [US4] Register admin router in apps/api/src/main.py (app.include_router with /v1 prefix)

**Checkpoint**: All 8 admin API endpoints functional. Auth guard blocks non-admin. Cross-tenant reads work. All mutations audit-logged. Latency percentiles included in metrics.

---

## Phase 6: User Story 3 — Admin Cockpit Dashboard (Priority: P3)

**Goal**: Admin cockpit at /admin with 6 sections: Users, Tenants, Health, Incidents, Rules, Access Control.

**Note**: Phase 6 runs AFTER Phase 5 (Admin API) because the cockpit consumes those endpoints.

**Independent Test**: Log in as admin, navigate to /admin, verify dashboard loads. Change a user role, verify audit log entry.

### Tests for User Story 3

- [x] T043 [P] [US3] Write e2e test for admin cockpit access control (admin sees dashboard, non-admin gets 403) in apps/web/tests/e2e/admin-access.test.ts
- [x] T044 [P] [US3] Write e2e test for admin user management (search user, change role, verify audit) in apps/web/tests/e2e/admin-users.test.ts

### Implementation for User Story 3

- [x] T045 [US3] Create admin layout with sidebar navigation in apps/web/src/routes/admin/+layout.svelte (Users, Tenants, Health, Incidents, Rules, Access sections)
- [x] T046 [US3] Create admin server-side role guard in apps/web/src/routes/admin/+layout.server.ts (redirect non-admin to dashboard with 403)
- [x] T047 [US3] Create admin dashboard overview page in apps/web/src/routes/admin/+page.svelte (summary cards for each section)
- [x] T048 [P] [US3] Create admin Users page in apps/web/src/routes/admin/users/+page.svelte (search, list, role change, deactivate, assign tenant)
- [x] T049 [P] [US3] Create admin Tenants page in apps/web/src/routes/admin/tenants/+page.svelte (list, usage metrics, plan tier)
- [x] T050 [P] [US3] Create admin Health page in apps/web/src/routes/admin/health/+page.svelte (request rate, p50/p95 latency, error rate, active scans, LLM usage with 60s auto-refresh)
- [x] T051 [P] [US3] Create admin Incidents page in apps/web/src/routes/admin/incidents/+page.svelte (total count, category distribution, severity distribution, embedding coverage)
- [x] T052 [P] [US3] Create admin Rules page in apps/web/src/routes/admin/rules/+page.svelte (active rules, false positive rate, synthesis candidates with approve/reject)
- [x] T053 [P] [US3] Create admin Access Control page in apps/web/src/routes/admin/access/+page.svelte (audit log, recent role changes)
- [x] T054 [US3] Add admin namespace to API client in apps/web/src/lib/api/client.ts (admin.users, admin.tenants, admin.metrics, admin.auditLog methods)

**Checkpoint**: Admin cockpit fully functional with all 6 sections. Non-admin blocked. Each section loads independently.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Security hardening, deployment verification, final integration.

- [x] T055 [P] Add Firebase authorized domain muscle.oute.pro in Firebase Console (manual step — document in quickstart.md)
- [x] T056 Add ADMIN_EMAILS, Firebase credentials, and ALLOWED_ORIGINS to GCP Secret Manager and Cloud Run env vars in infra/gcp/modules/cloud-run/main.tf
- [x] T057 Run quickstart.md validation scenarios (all 8 scenarios) as acceptance tests
- [x] T058 Verify Ruff lint passes on all modified Python files
- [x] T059 Verify svelte-check passes on all modified Svelte/TS files

**Checkpoint**: All scenarios from quickstart.md pass. Lint clean. Firebase domain authorized. Secrets in Secret Manager.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user stories
- **Phase 3 (US1 — Firebase Auth)**: Depends on Phase 2 — delivers login MVP
- **Phase 4 (US2 — Custom Domain)**: Depends on Phase 1 only — can run in parallel with Phase 3
- **Phase 5 (US4 — Admin API)**: Depends on Phase 2 (needs User model changes) — can run in parallel with Phase 3
- **Phase 6 (US3 — Admin Cockpit UI)**: Depends on Phase 3 (needs auth) + Phase 5 (needs admin API)
- **Phase 7 (Polish)**: Depends on all prior phases

### User Story Dependencies

- **US1 (P1)**: After Foundational — no dependencies on other stories
- **US2 (P2)**: After Setup only — independent of auth (infra work)
- **US4 (P4)**: After Foundational — independent of US1 (API uses existing JWT/API-key auth)
- **US3 (P3)**: After US1 (needs auth) + US4 (needs admin API data)

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models/migration before services
- Server-side before client-side
- Core implementation before integration

### Parallel Opportunities

- Phase 3 (US1 — Auth) and Phase 4 (US2 — Domain) can run in parallel after Foundational
- Phase 3 (US1) and Phase 5 (US4 — Admin API) can run in parallel after Foundational
- All [P] tasks within a phase can run in parallel
- Admin cockpit pages (T048-T053) are all parallelizable

---

## Parallel Example: Phase 6 (Admin Cockpit)

```bash
# Launch all admin section pages in parallel:
Task: T048 — Users page (different file)
Task: T049 — Tenants page (different file)
Task: T050 — Health page (different file)
Task: T051 — Incidents page (different file)
Task: T052 — Rules page (different file)
Task: T053 — Access Control page (different file)
```

## Parallel Example: Phase 5 (Admin API)

```bash
# After T035 (base admin routes file), endpoints can be added in sequence
# But test writing is parallel:
Task: T030 — Auth guard tests (different file)
Task: T031 — User management tests (different file)
Task: T032 — Cross-tenant integration tests (different file)
```

---

## Implementation Strategy

### MVP First (Phase 1-3: Firebase Auth Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (Firebase SDK, User model, auth hooks)
3. Complete Phase 3: Firebase Auth (login, session, JIT provisioning)
4. **STOP and VALIDATE**: Sign in with Google, verify session works, verify pending page for new users
5. Deploy — Firebase Auth delivers immediate value

### Incremental Delivery

1. Phase 1-3 → Firebase Auth MVP (users can sign in)
2. Phase 4 → Custom Domain (muscle.oute.pro live)
3. Phase 5 → Admin API (backend ready for cockpit)
4. Phase 6 → Admin Cockpit UI (platform operations)
5. Phase 7 → Polish (security, secrets, final verification)

### Parallel Team Strategy

With multiple developers:

1. Team completes Phase 1-2 together
2. Once Foundational is done:
   - Developer A: Phase 3 (Firebase Auth — MVP)
   - Developer B: Phase 4 (Domain mapping — infra) + Phase 5 (Admin API)
3. After Phase 3+5:
   - Developer A: Phase 6 (Admin Cockpit UI)
   - Developer B: Phase 7 (Polish)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each phase is independently completable and testable
- DNS records (CNAME) for muscle.oute.pro and mcp.muscle.oute.pro already configured by user
- Firebase project oute-488706 shared with oute.me — same user pool
- SvelteKit acts as BFF — FastAPI API stays Firebase-free; SvelteKit proxies /api/* to FastAPI
- Admin bypasses RLS for cross-tenant reads
