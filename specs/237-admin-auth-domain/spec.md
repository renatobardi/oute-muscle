# Feature Specification: Admin Cockpit, Firebase Auth & Custom Domain

**Feature Branch**: `237-admin-auth-domain`
**Created**: 2026-03-29
**Status**: Draft
**Input**: User description: "Web app at muscle.oute.pro, admin cockpit (/admin) for full platform management, Firebase authentication (email + Google) sharing users with oute.me project"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Firebase Authentication (Email + Google) (Priority: P1)

A user navigates to muscle.oute.pro and sees a login page. They can sign in using their email/password or their Google account. The authentication is handled by Firebase, sharing the same user pool as the oute.me project (Firebase project `oute-488706`). After successful login, the user receives a secure session and is redirected to the dashboard. Users who already have an account on oute.me can sign in to muscle.oute.pro with the same credentials without re-registering. New users can create an account that works across both platforms.

**Why this priority**: Authentication is the foundation — nothing else works without it. Sharing the Firebase user pool with oute.me enables a unified identity across the Oute ecosystem.

**Independent Test**: Navigate to muscle.oute.pro/auth/login, sign in with a Google account that was previously used on oute.me, verify the user is authenticated and redirected to the dashboard with correct role and tenant context.

**Acceptance Scenarios**:

1. **Given** a user with an existing oute.me account, **When** they navigate to muscle.oute.pro and sign in with Google, **Then** they are authenticated, a session is created, and they see the dashboard with their tenant context.
2. **Given** a new user, **When** they sign up with email/password on muscle.oute.pro, **Then** the account is created in Firebase, they are authenticated, and the same credentials work on oute.me.
3. **Given** a user on the login page, **When** they click "Sign in with Google", **Then** Google One Tap or popup flow opens, authenticates the user, and redirects to the dashboard.
4. **Given** an authenticated user, **When** their session expires, **Then** they are redirected to the login page with a message explaining the session expired.
5. **Given** a user with an invalid or expired Firebase token, **When** they attempt to access any protected route, **Then** they are redirected to the login page.

---

### User Story 2 — Custom Domain (muscle.oute.pro) (Priority: P2)

The Oute Muscle web application is accessible at `muscle.oute.pro`. The API responds at `muscle.oute.pro/api`. The MCP Server responds at `mcp.muscle.oute.pro`. All traffic is served over HTTPS with valid certificates. No provisional Cloud Run URLs are exposed to end users — all public-facing access goes through the custom domain.

**Why this priority**: A stable, branded domain is essential for user trust and for Firebase auth callback URLs. Without it, Firebase OAuth redirect URIs cannot be properly configured and the product cannot be shared externally.

**Independent Test**: Open a browser, navigate to `https://muscle.oute.pro`, verify the page loads with a valid HTTPS certificate and the correct application content. Verify `https://muscle.oute.pro/api/v1/health` returns 200.

**Acceptance Scenarios**:

1. **Given** the domain `muscle.oute.pro` is configured, **When** a user navigates to `https://muscle.oute.pro`, **Then** the SvelteKit dashboard loads with a valid TLS certificate.
2. **Given** the API is deployed, **When** a client calls `https://muscle.oute.pro/api/v1/health`, **Then** the API responds with HTTP 200.
3. **Given** the MCP Server is deployed, **When** a client connects to `https://mcp.muscle.oute.pro`, **Then** the MCP Server responds with the correct Streamable HTTP handshake.
4. **Given** a user navigates to the raw Cloud Run URL, **When** the request reaches the service, **Then** the response redirects to the canonical `muscle.oute.pro` domain or the raw URL is not publicly accessible.
5. **Given** CORS is configured, **When** `muscle.oute.pro` makes an API request, **Then** the request is allowed. Requests from other origins are rejected.

---

### User Story 3 — Admin Cockpit Dashboard (Priority: P3)

A platform administrator (identified by the `admin` role or by matching an admin email list) accesses `/admin` and sees a comprehensive operational cockpit. The cockpit provides full visibility into: user management (all users across tenants, roles, access grants), tenant operations (plans, usage, billing status), platform health (API latency, error rates, active scans), incident knowledge base metrics (total incidents, category distribution, embedding coverage), rule metrics (active rules, false positive rates, synthesis candidates), and access control (pending invitations, role changes, audit trail). The admin can perform actions: grant/revoke access, change user roles, approve/reject tenant upgrades, enable/disable rules globally, and view the full audit log.

**Why this priority**: The admin cockpit is the operational backbone of the platform. Without it, the platform operator has no visibility into usage, health, or access control — making it impossible to support customers or manage the product.

**Independent Test**: Log in as an admin user, navigate to `/admin`, verify the dashboard loads with real-time metrics. Grant a user editor access, verify the change takes effect immediately.

**Acceptance Scenarios**:

1. **Given** an admin user is authenticated, **When** they navigate to `/admin`, **Then** the cockpit dashboard loads with sections for users, tenants, health, incidents, rules, and access control.
2. **Given** a non-admin user, **When** they navigate to `/admin`, **Then** they receive a 403 Forbidden page and are redirected to the regular dashboard.
3. **Given** the admin is on the Users section, **When** they search for a user by email, **Then** the system returns the user's profile including: tenant, role, last login, created date, and activity summary.
4. **Given** the admin is on the Users section, **When** they change a user's role from viewer to editor, **Then** the role is updated immediately, an audit log entry is created, and the user's next request reflects the new permissions.
5. **Given** the admin is on the Tenants section, **When** they view a tenant, **Then** they see: plan tier, contributor count, repo count, scan count (last 30 days), findings count, and billing status.
6. **Given** the admin is on the Platform Health section, **When** the dashboard loads, **Then** they see real-time metrics: API request rate, p50/p95 latency, error rate, active scans, and LLM usage per model.
7. **Given** the admin is on the Rules section, **When** they view synthesis candidates, **Then** they can approve or reject candidates, and approved rules are promoted to Layer 1.
8. **Given** the admin is on the Access Control section, **When** they view the audit log, **Then** they see a chronological list of all mutations with who, when, and what changed.

---

### User Story 4 — Admin API Endpoints (Priority: P4)

The admin cockpit is powered by dedicated API endpoints under `/v1/admin/` that provide aggregated data and administrative actions. These endpoints are protected by admin-role authentication and return data across all tenants (bypassing RLS for read operations). Mutations are audit-logged.

**Why this priority**: The admin API is the data layer for the cockpit. Without it, the dashboard has no data to display.

**Independent Test**: Authenticate as an admin, call `GET /v1/admin/users`, verify the response includes users from multiple tenants with their roles and activity.

**Acceptance Scenarios**:

1. **Given** an admin-authenticated request, **When** `GET /v1/admin/users` is called, **Then** the response includes all users across all tenants with: id, email, tenant, role, last_login, created_at.
2. **Given** an admin-authenticated request, **When** `GET /v1/admin/tenants` is called, **Then** the response includes all tenants with: id, name, plan_tier, contributor_count, repo_count, scan_count_30d, is_active.
3. **Given** an admin-authenticated request, **When** `POST /v1/admin/users/{id}/role` is called with `{"role": "editor"}`, **Then** the user's role is updated and an audit log entry is created.
4. **Given** a non-admin request, **When** any `/v1/admin/` endpoint is called, **Then** the response is 403 Forbidden.
5. **Given** an admin-authenticated request, **When** `GET /v1/admin/metrics` is called, **Then** the response includes aggregated platform metrics (scan counts, finding counts, LLM usage, error rates).

---

### Edge Cases

- What happens when a Firebase user exists but has no corresponding record in the Oute Muscle database? The system creates a default user record with viewer role on first login (just-in-time provisioning).
- What happens when the Firebase service is unavailable? The login page shows an error message "Authentication service temporarily unavailable. Please try again." Protected routes that have valid session cookies continue to work until the session expires.
- What happens when an admin removes their own admin role? The system prevents self-demotion — an admin cannot change their own role. Another admin must do it.
- What happens when a user is deleted in Firebase but still has an active session in Oute Muscle? On the next token refresh (within 1 hour), the session is invalidated and the user is redirected to login.
- What happens when the DNS for muscle.oute.pro is not yet propagated? The raw Cloud Run URL continues to serve traffic as a fallback during the DNS propagation window (up to 48 hours).
- What happens when the admin dashboard loads but the metrics API is slow or down? Each dashboard section loads independently. Sections with failed API calls show "Unable to load data — Retry" instead of blocking the entire page.

## Requirements *(mandatory)*

### Functional Requirements

**Authentication (Firebase)**

- **FR-001**: System MUST authenticate users via Firebase Authentication using the shared Firebase project `oute-488706`, supporting email/password and Google sign-in providers.
- **FR-002**: System MUST use Firebase ID tokens for authentication, verified server-side via Firebase Admin SDK. Session management MUST use secure HTTP-only cookies with a maximum age of 5 days, matching the oute.me pattern.
- **FR-003**: System MUST perform just-in-time user provisioning — when a Firebase-authenticated user logs in for the first time and has no record in the Oute Muscle database, the system creates a user record with default role (viewer) and no tenant association. The user sees a "pending approval" landing page until an admin assigns them to a tenant via the admin cockpit.
- **FR-004**: System MUST support the existing role model (viewer, editor, admin) with role stored in the Oute Muscle database, not in Firebase custom claims.
- **FR-005**: System MUST determine admin status from an environment-configurable admin email list (ADMIN_EMAILS), matching the oute.me pattern. Users whose email matches the list are granted admin role on first login.

**Custom Domain**

- **FR-006**: The web application MUST be accessible at `https://muscle.oute.pro` with a valid TLS certificate managed by GCP.
- **FR-007**: The API MUST be accessible at `https://muscle.oute.pro/api/v1/` via the SvelteKit Cloud Run service acting as a BFF (Backend For Frontend) — SvelteKit proxies `/api/*` requests to the FastAPI Cloud Run service internally.
- **FR-008**: The MCP Server MUST be accessible at `https://mcp.muscle.oute.pro` with a valid TLS certificate.
- **FR-009**: CORS configuration MUST restrict allowed origins to `https://muscle.oute.pro` and `https://oute.pro` (and localhost for development). The current wildcard `*` MUST be replaced.
- **FR-010**: Firebase Authentication MUST be configured with `muscle.oute.pro` as an authorized domain for OAuth redirect URIs.

**Admin Cockpit**

- **FR-011**: System MUST provide an admin cockpit at `/admin` accessible only to users with admin role.
- **FR-012**: The admin cockpit MUST display a Users section showing all users across all tenants with: email, display name, tenant name, role, last login, created date, and account status.
- **FR-013**: The admin cockpit MUST allow admins to: search users by email/name, change user roles, deactivate/reactivate user accounts, and assign users to tenants.
- **FR-014**: The admin cockpit MUST display a Tenants section showing all tenants with: name, plan tier, contributor count, repository count, scan count (last 30 days), findings count, and active/inactive status.
- **FR-015**: The admin cockpit MUST display a Platform Health section with real-time metrics: API request rate, p50/p95 response latency, error rate (4xx/5xx), active scans count, and LLM usage breakdown per model (Flash/Pro/Claude).
- **FR-016**: The admin cockpit MUST display an Incidents section with: total incident count, category distribution chart, severity distribution, embedding coverage percentage, and recent additions.
- **FR-017**: The admin cockpit MUST display a Rules section with: active rule count, false positive rate (reports vs total findings), synthesis candidates pending review, and auto-disabled rules.
- **FR-018**: The admin cockpit MUST display an Access Control section with: pending invitations, recent role changes, and a full audit log with who/when/what-changed.
- **FR-019**: The admin cockpit MUST allow admins to approve or reject synthesis candidates directly from the Rules section, with the same effect as the existing synthesis approval flow.
- **FR-020**: All admin mutations (role changes, access grants, rule approvals) MUST be recorded in the audit log.

**Admin API**

- **FR-021**: System MUST expose admin API endpoints under `/v1/admin/` prefix, protected by admin-role authentication middleware.
- **FR-022**: Admin API read endpoints MUST bypass RLS to return data across all tenants.
- **FR-023**: Admin API MUST expose: `GET /v1/admin/users`, `GET /v1/admin/tenants`, `GET /v1/admin/metrics`, `POST /v1/admin/users/{id}/role`, `POST /v1/admin/users/{id}/deactivate`, `POST /v1/admin/users/{id}/activate`, `POST /v1/admin/users/{id}/assign-tenant`, `GET /v1/admin/audit-log`.

### Key Entities

- **Firebase User**: A user identity managed by Firebase Authentication (uid, email, display_name, provider, email_verified). Shared across oute.me and oute-muscle. Linked to the Oute Muscle User entity via a `firebase_uid` field (string, unique, indexed) — the internal UUID remains the primary key for all FK/RLS relationships.
- **Admin Session**: A secure HTTP-only cookie containing a Firebase session token, verified server-side on each request. Maximum lifetime 5 days.
- **Admin Metrics**: Aggregated operational data (request rates, latencies, scan counts, LLM usage) computed from existing observability infrastructure and database queries. Not a persisted entity.
- **Domain Mapping**: A GCP Cloud Run domain mapping that binds `muscle.oute.pro` to the Cloud Run service with GCP-managed TLS certificate.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can sign in to muscle.oute.pro using their existing oute.me credentials (email or Google) in under 5 seconds.
- **SC-002**: The admin cockpit loads all dashboard sections within 3 seconds on initial page load.
- **SC-003**: 100% of admin mutations (role changes, access grants) are recorded in the audit log within 1 second of the action.
- **SC-004**: The custom domain `muscle.oute.pro` serves all traffic with a valid TLS certificate and zero downtime after initial setup.
- **SC-005**: Non-admin users attempting to access `/admin` receive a 403 response 100% of the time.
- **SC-006**: The admin can search and find any user across all tenants by email in under 2 seconds.
- **SC-007**: Platform health metrics in the admin cockpit refresh at least every 60 seconds without manual page reload.

## Clarifications

### Session 2026-03-29

- Q: Should the Firebase integration replace the existing OAuth 2.1 flow or coexist? A: Replace. Firebase becomes the sole authentication provider for the web application. The MCP Server retains its own OAuth 2.1 flow (FR-030 from spec 001) as it serves IDE clients, not browser users.
- Q: Should the API also accept Firebase tokens directly, or only session cookies? A: The web frontend uses session cookies (server-side rendered). External API consumers (REST API for GitLab/Bitbucket) continue using API keys (existing auth middleware). Firebase tokens are exchanged for session cookies at login time only.
- Q: How to link Firebase UID to the existing User model? A: Add a `firebase_uid` (string, unique, indexed) field to the User model. Internal UUID stays as PK for all FK/RLS.
- Q: How is a new JIT-provisioned user associated to a tenant? A: User stays tenant-less until an admin assigns them via the cockpit. They see a "pending approval" page until then.
- Q: Where should the DNS for oute.pro be managed? A: DNS is managed externally (likely Cloudflare or the domain registrar). The Terraform config only creates the Cloud Run domain mapping; DNS records (CNAME) must be created manually or via a separate DNS provider module.

## Assumptions

- The Firebase project `oute-488706` is already configured with email/password and Google authentication providers (confirmed from oute.me project).
- DNS for `oute.pro` is managed by the user outside of GCP (Cloudflare, Namecheap, etc.). The CNAME records pointing `muscle.oute.pro` and `mcp.muscle.oute.pro` to Cloud Run will be created manually by the user.
- The existing session cookie pattern from oute.me (5-day max age, HTTP-only, secure, SameSite=Lax) is appropriate for oute-muscle.
- The Firebase Admin SDK on Cloud Run will use Application Default Credentials (ADC) — no service account key files needed.
- The admin email list (ADMIN_EMAILS) is managed as an environment variable, not a database table. This matches the oute.me pattern and is sufficient for a small team of platform operators.
- The SvelteKit adapter will be changed from `adapter-auto` to `adapter-node` for Cloud Run deployment with server-side rendering and session cookie support.
- The admin cockpit is for platform operators only (Oute team), not for tenant admins. Tenant admins continue using the existing `/settings` page for their tenant management.
- Platform health metrics are derived from existing observability infrastructure (OpenTelemetry metrics) and database aggregation queries — no new metrics collection system is needed.
