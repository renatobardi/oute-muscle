# API Contract: Authentication (Firebase)

**Base URL**: `https://muscle.oute.pro`

## SvelteKit Server Endpoints

### POST /api/auth/session

Exchange Firebase ID token for a session cookie.

**Request**:
```json
{ "idToken": "eyJhbGciOi..." }
```

**Response 200** (Set-Cookie: __session):
```json
{
  "status": "ok",
  "user": {
    "uid": "firebase-uid",
    "email": "user@example.com",
    "display_name": "John Doe",
    "role": "viewer | editor | admin",
    "tenant_id": "uuid | null",
    "pending_approval": true
  }
}
```

**Response 401**: Invalid or expired Firebase token.

### DELETE /api/auth/session

Logout — revoke session and clear cookie.

**Response 200**:
```json
{ "status": "logged_out" }
```

## Session Cookie

| Property | Value |
|----------|-------|
| Name | `__session` |
| Max-Age | 432000 (5 days) |
| HttpOnly | true |
| Secure | true |
| SameSite | Lax |
| Path | / |

## Auth Guard (hooks.server.ts)

Every request passes through:
1. `authenticate`: Verify `__session` cookie via Firebase Admin SDK
2. `gateUser`: Check user state (pending approval, deactivated, etc.)

Protected routes redirect to `/auth/login` if unauthenticated.
Pending-approval users see `/pending` landing page.
