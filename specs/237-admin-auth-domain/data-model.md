# Data Model: Admin Cockpit, Firebase Auth & Custom Domain

**Branch**: `237-admin-auth-domain` | **Date**: 2026-03-29

## Entity Changes

### User (MODIFY existing)

Add fields to `packages/db/src/models/user.py`:

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| firebase_uid | String(128) | UNIQUE, NOT NULL, INDEXED | Firebase Authentication UID, links to shared user pool |
| display_name | String(255) | nullable | From Firebase profile (Google display name or custom) |
| email_verified | Boolean | NOT NULL, default false | Mirrors Firebase email_verified state |
| last_login | DateTime | nullable | Updated on each successful session creation |
| is_active | Boolean | NOT NULL, default true | Admin can deactivate accounts |

**Identity rule**: `firebase_uid` is the external identity key. Internal `id` (UUID) remains PK for all FK/RLS relationships. One-to-one with Firebase user.

**Lifecycle**: Created → Active (normal) → Deactivated (admin action) → Reactivated (admin action). Deletion is not supported (soft-disable via `is_active`).

### Tenant (MODIFY existing)

No schema changes needed for this feature. Existing fields (`id`, `name`, `slug`, `plan_tier`, `is_active`) are sufficient for admin cockpit display.

### AuditLogEntry (MODIFY existing)

Add action values for admin operations:

| Action | Entity Type | Description |
|--------|-------------|-------------|
| role_change | user | Admin changed user role |
| deactivate | user | Admin deactivated user account |
| reactivate | user | Admin reactivated user account |
| assign_tenant | user | Admin assigned user to tenant |

No schema changes needed — existing `action` (String) and `changes` (JSONB) fields support these.

### Domain Mapping (Infrastructure only)

Not a database entity. Managed by Terraform (`google_cloud_run_domain_mapping` resource). State tracked in Terraform state file.

## Migration Required

New Alembic migration `004_firebase_auth_fields.py`:
- Add `firebase_uid` (String, unique, indexed) to `user` table
- Add `display_name` (String, nullable) to `user` table
- Add `email_verified` (Boolean, default false) to `user` table
- Add `last_login` (DateTime, nullable) to `user` table

The `is_active` field already exists on the User model.

## Relationships

```
Firebase Auth (external)
    │
    │ firebase_uid (1:1)
    ▼
User ──── tenant_id (N:1) ────► Tenant
  │
  │ performed_by (1:N)
  ▼
AuditLogEntry
```

## Admin Query Patterns

Admin API endpoints bypass RLS and query across all tenants:

- **Users list**: `SELECT u.*, t.name as tenant_name FROM user u LEFT JOIN tenant t ON u.tenant_id = t.id ORDER BY u.created_at DESC`
- **Tenants list**: `SELECT t.*, COUNT(u.id) as contributor_count, COUNT(DISTINCT s.id) as scan_count_30d FROM tenant t LEFT JOIN user u ON ... LEFT JOIN scan s ON ... GROUP BY t.id`
- **Metrics**: Aggregation queries over `scan`, `finding`, `incident`, `semgrep_rule` tables with no tenant filter
