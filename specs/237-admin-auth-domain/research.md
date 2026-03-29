# Research: Admin Cockpit, Firebase Auth & Custom Domain

**Branch**: `237-admin-auth-domain` | **Date**: 2026-03-29

## R1: Firebase Auth Integration Strategy

**Decision**: Replace custom OAuth 2.1 flow with Firebase Auth (client SDK + Admin SDK), using session cookies for SSR.

**Rationale**: Firebase project `oute-488706` already exists with email/password + Google providers configured in oute.me. Session cookie pattern (5-day, httpOnly, secure) is production-proven in oute.me. Eliminates custom PKCE implementation and key management.

**Alternatives considered**:
- Keep OAuth 2.1 + add Firebase as secondary provider — rejected: dual auth flows increase complexity without benefit.
- Firebase custom tokens from FastAPI — rejected: requires running Firebase Admin SDK on Python side for every request; session cookie approach keeps verification in SvelteKit server hooks.

**Key patterns from oute.me**:
- Client: `firebase.ts` singleton → `getAuth()` → `signInWithPopup(GoogleAuthProvider)` or `signInWithEmailAndPassword()`
- Server: `firebase-admin.ts` → `getAdminAuth().verifyIdToken()` → `createSessionCookie()` (5 days)
- Session exchange: `POST /api/auth/session` with idToken → sets httpOnly cookie
- Auth guard: SvelteKit `hooks.server.ts` with `sequence(authenticate, gateUser)`
- DB sync: `getOrCreateUser(firebaseUid, email, displayName)` on each login

## R2: SvelteKit SSR Adapter

**Decision**: Switch from `adapter-auto` to `adapter-node` for Cloud Run deployment.

**Rationale**: Session cookies and server-side Firebase Admin SDK verification require a Node.js server runtime. `adapter-auto` may select static adapter in some environments. `adapter-node` guarantees Express-compatible server with `hooks.server.ts` support.

**Alternatives considered**:
- `adapter-cloudflare` — rejected: project deploys on GCP Cloud Run, not Cloudflare Workers.
- Keep `adapter-auto` — rejected: unpredictable behavior for session management.

## R3: Cloud Run Domain Mapping

**Decision**: Use `google_cloud_run_domain_mapping` Terraform resource for `muscle.oute.pro` and `mcp.muscle.oute.pro`. DNS managed externally (user creates CNAME records).

**Rationale**: Cloud Run native domain mapping provides GCP-managed TLS certificates (auto-renew). No need for external load balancer or certificate manager.

**Alternatives considered**:
- GCP Global External HTTP(S) Load Balancer + Cloud CDN — rejected: overkill for current scale; adds cost and complexity. Can migrate later if needed.
- Cloudflare proxy — rejected: adds external dependency; project is GCP-native per Constitution IV.

## R4: Admin API RLS Bypass

**Decision**: Admin API endpoints use sessions without RLS (no `SET LOCAL "app.tenant_id"`). Admin middleware verifies role=admin and uses a standard `AsyncSession` without tenant scoping.

**Rationale**: Admin needs cross-tenant read access. Existing `TenantContextSession` always sets tenant context, which would filter out other tenants' data.

**Alternatives considered**:
- Add "superuser" tenant context that bypasses RLS policies — rejected: requires PostgreSQL policy changes and creates security surface.
- Use separate DB connection pool for admin — rejected: unnecessary; just skip the `SET LOCAL` call.

## R5: API Auth for Firebase (Backend)

**Decision**: The FastAPI API continues accepting JWT Bearer tokens and API keys. For web dashboard requests, the SvelteKit server-side calls the API with a service-level token or internal header. Firebase tokens are NOT sent directly to the FastAPI API.

**Rationale**: The SvelteKit app handles Firebase auth (session cookies) and acts as a BFF (Backend For Frontend). The FastAPI API doesn't need Firebase SDK — it trusts the SvelteKit server's forwarded auth context. This keeps the API auth simple and Firebase-free.

**Alternatives considered**:
- Add Firebase Admin SDK to FastAPI — rejected: adds Python dependency, duplicates verification logic, and complicates the auth middleware.
- Pass Firebase tokens directly from browser to API — rejected: session cookies are httpOnly (not accessible to JS); would need to change security model.

## R6: Admin Cockpit Architecture

**Decision**: Admin cockpit is a SvelteKit route group at `/admin/` with its own layout, connecting to admin API endpoints (`/v1/admin/`). Each section loads independently with client-side fetching.

**Rationale**: Leverages existing SvelteKit patterns (route groups, layouts). Independent section loading (FR from spec) means each card/section calls its own API endpoint, improving perceived performance and resilience.

**Alternatives considered**:
- Separate admin SPA — rejected: doubles frontend maintenance; SvelteKit route groups provide sufficient isolation.
- Server-side rendered admin pages — rejected: admin cockpit needs real-time metrics refresh (polling), better suited for client-side fetching with SvelteKit's hybrid approach.
