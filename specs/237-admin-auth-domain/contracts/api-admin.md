# API Contract: Admin Endpoints

**Base URL**: `https://muscle.oute.pro/api/v1/admin`
**Auth**: Session cookie (via SvelteKit BFF) with admin role verified

## Endpoints

### GET /admin/users

List all users across all tenants.

**Query params**: `?q=search&role=admin&tenant_id=uuid&page=1&per_page=50`

**Response 200**:
```json
{
  "items": [
    {
      "id": "uuid",
      "firebase_uid": "string",
      "email": "user@example.com",
      "display_name": "John Doe",
      "tenant_id": "uuid | null",
      "tenant_name": "Acme Corp | null",
      "role": "viewer | editor | admin",
      "is_active": true,
      "email_verified": true,
      "last_login": "2026-03-29T10:00:00Z",
      "created_at": "2026-03-01T00:00:00Z"
    }
  ],
  "total": 150,
  "page": 1,
  "per_page": 50
}
```

### GET /admin/tenants

List all tenants with usage metrics.

**Query params**: `?q=search&plan_tier=team&is_active=true&page=1&per_page=50`

**Response 200**:
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Acme Corp",
      "slug": "acme-corp",
      "plan_tier": "free | team | enterprise",
      "is_active": true,
      "contributor_count": 12,
      "repo_count": 5,
      "scan_count_30d": 340,
      "findings_count_30d": 42,
      "created_at": "2026-01-15T00:00:00Z"
    }
  ],
  "total": 25,
  "page": 1,
  "per_page": 50
}
```

### GET /admin/metrics

Aggregated platform metrics.

**Response 200**:
```json
{
  "users": { "total": 150, "active_30d": 85 },
  "tenants": { "total": 25, "active": 20 },
  "scans": { "total_30d": 1200, "active_now": 3 },
  "findings": { "total_30d": 450, "by_severity": { "critical": 5, "high": 40, "medium": 200, "low": 205 } },
  "incidents": { "total": 53, "with_embedding": 50, "by_category": { "unsafe-regex": 4, "...": "..." } },
  "rules": { "active": 10, "auto_disabled": 0, "synthesis_pending": 2 },
  "llm_usage_30d": { "flash": 800, "pro": 150, "claude": 50 }
}
```

### POST /admin/users/{id}/role

Change a user's role.

**Request**:
```json
{ "role": "viewer | editor | admin" }
```

**Response 200**:
```json
{ "id": "uuid", "email": "user@example.com", "role": "editor", "updated_at": "2026-03-29T10:00:00Z" }
```

**Response 400**: Self-demotion attempted.
**Response 404**: User not found.

### POST /admin/users/{id}/deactivate

Deactivate a user account.

**Response 200**:
```json
{ "id": "uuid", "is_active": false, "updated_at": "2026-03-29T10:00:00Z" }
```

### POST /admin/users/{id}/activate

Reactivate a user account.

**Response 200**:
```json
{ "id": "uuid", "is_active": true, "updated_at": "2026-03-29T10:00:00Z" }
```

### POST /admin/users/{id}/assign-tenant

Assign a user to a tenant.

**Request**:
```json
{ "tenant_id": "uuid" }
```

**Response 200**:
```json
{ "id": "uuid", "tenant_id": "uuid", "tenant_name": "Acme Corp", "updated_at": "2026-03-29T10:00:00Z" }
```

### GET /admin/audit-log

Full audit log across all tenants.

**Query params**: `?entity_type=user&action=role_change&from=2026-01-01&to=2026-03-29&page=1&per_page=50`

**Response 200**:
```json
{
  "items": [
    {
      "id": "uuid",
      "tenant_id": "uuid | null",
      "action": "role_change",
      "entity_type": "user",
      "entity_id": "uuid",
      "performed_by": "uuid",
      "performed_by_email": "admin@example.com",
      "changes": { "before": { "role": "viewer" }, "after": { "role": "editor" } },
      "created_at": "2026-03-29T10:00:00Z"
    }
  ],
  "total": 200,
  "page": 1,
  "per_page": 50
}
```

## Error Responses

All endpoints return:
- **401**: Not authenticated
- **403**: Not admin role
- **500**: Internal server error

```json
{ "error": "Description", "code": "ERROR_CODE" }
```
