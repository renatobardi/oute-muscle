# Quickstart: Admin Cockpit, Firebase Auth & Custom Domain

**Branch**: `237-admin-auth-domain` | **Date**: 2026-03-29

## Scenario 1: Firebase Login (Google)

1. Navigate to `https://muscle.oute.pro/auth/login`
2. Click "Sign in with Google"
3. Select Google account (same as used on oute.me)
4. **Expected**: Redirected to dashboard. Session cookie set. User record created (JIT provisioning) if first login.

## Scenario 2: Firebase Login (Email/Password)

1. Navigate to `https://muscle.oute.pro/auth/login`
2. Enter email and password
3. Click "Sign in"
4. **Expected**: Authenticated and redirected to dashboard. Works with existing oute.me credentials.

## Scenario 3: New User (Pending Approval)

1. Sign up with a new email/password on muscle.oute.pro
2. **Expected**: Account created in Firebase. User record created in DB with role=viewer, tenant_id=null.
3. **Expected**: User sees "Pending Approval" landing page explaining that an admin needs to assign them to a tenant.
4. Admin navigates to `/admin` → Users → finds the new user → assigns to tenant.
5. User refreshes page → now sees the full dashboard.

## Scenario 4: Custom Domain Verification

1. Open browser, navigate to `https://muscle.oute.pro`
2. **Expected**: Valid TLS certificate (GCP-managed), SvelteKit dashboard loads.
3. Navigate to `https://muscle.oute.pro/api/v1/health`
4. **Expected**: API responds with HTTP 200 and JSON health status.
5. Navigate to `https://mcp.muscle.oute.pro`
6. **Expected**: MCP Server responds (Streamable HTTP handshake).

## Scenario 5: Admin Cockpit Access

1. Log in with an email matching `ADMIN_EMAILS` env var
2. Navigate to `/admin`
3. **Expected**: Cockpit loads with 6 sections: Users, Tenants, Health, Incidents, Rules, Access Control.
4. Click Users section → search by email → change a user's role
5. **Expected**: Role updated, audit log entry created.

## Scenario 6: Non-Admin Access Denied

1. Log in with a non-admin account
2. Navigate to `/admin`
3. **Expected**: 403 Forbidden page, redirected to regular dashboard.

## Scenario 7: CORS Enforcement

1. From a page on `https://evil-site.com`, make a fetch to `https://muscle.oute.pro/api/v1/health`
2. **Expected**: CORS error — origin not in allowed list.
3. From `https://muscle.oute.pro`, make a fetch to the API
4. **Expected**: Request succeeds.

## Scenario 8: Session Expiry

1. Log in and receive session cookie (5-day max)
2. Wait for session to expire (or manually delete the cookie)
3. Navigate to any protected route
4. **Expected**: Redirected to `/auth/login` with "Session expired" message.
