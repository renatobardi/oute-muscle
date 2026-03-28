# Data Model: Incident-Based Code Guardrails Platform

**Branch**: `001-incident-code-guardrails` | **Date**: 2026-03-28

## Entity Relationship Overview

```text
Tenant 1──* User
Tenant 1──* Incident (tenant-specific)
Tenant 1──* SemgrepRule (tenant-specific)
Tenant 1──* Scan
Tenant 1──* TenantConfig

Incident *──* SemgrepRule (via incident_rule link)
Incident 1──* AuditLogEntry
SemgrepRule 1──* Finding
SemgrepRule 1──* AuditLogEntry
Scan 1──* Finding
Scan 1──* Advisory

User 1──* AuditLogEntry (actor)

Note: tenant_id IS NULL = shared/public record (knowledge base, public rules)
```

## Entities

### Tenant

| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | PK, generated |
| name | VARCHAR(255) | NOT NULL |
| slug | VARCHAR(100) | UNIQUE, NOT NULL |
| plan_tier | ENUM('free', 'team', 'enterprise') | NOT NULL, DEFAULT 'free' |
| max_contributors | INTEGER | NOT NULL (derived from plan) |
| max_repos | INTEGER | NOT NULL (derived from plan) |
| rate_limit_rpm | INTEGER | NOT NULL (30/120/600 by tier) |
| github_installation_id | BIGINT | NULLABLE, UNIQUE |
| api_key_hash | VARCHAR(64) | NULLABLE (for REST API auth) |
| sso_config | JSONB | NULLABLE (Enterprise only) |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() |

**RLS**: No RLS on tenants table (accessed by auth middleware to resolve context).

### User

| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | PK, generated |
| tenant_id | UUID | FK → Tenant, NOT NULL |
| email | VARCHAR(255) | NOT NULL, UNIQUE within tenant |
| name | VARCHAR(255) | NOT NULL |
| role | ENUM('viewer', 'editor', 'admin') | NOT NULL, DEFAULT 'viewer' |
| oauth_provider | VARCHAR(50) | NULLABLE (github, google, saml) |
| oauth_subject | VARCHAR(255) | NULLABLE |
| password_hash | VARCHAR(255) | NULLABLE (for email/password auth) |
| refresh_token_hash | VARCHAR(64) | NULLABLE |
| mcp_monthly_scans | INTEGER | NOT NULL, DEFAULT 0 |
| mcp_quota_reset_at | TIMESTAMPTZ | NOT NULL |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() |
| last_login_at | TIMESTAMPTZ | NULLABLE |

**RLS**: `tenant_id = current_setting('app.tenant_id')::uuid`

### Incident

| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | PK, generated |
| tenant_id | UUID | FK → Tenant, NULLABLE (NULL = shared/public) |
| title | VARCHAR(500) | NOT NULL |
| date | DATE | NULLABLE |
| source_url | VARCHAR(2048) | NULLABLE, UNIQUE (for dedup) |
| organization | VARCHAR(255) | NULLABLE |
| category | ENUM (10 categories) | NOT NULL |
| subcategory | VARCHAR(100) | NULLABLE |
| failure_mode | TEXT | NULLABLE |
| severity | ENUM('critical', 'high', 'medium', 'low') | NOT NULL |
| affected_languages | VARCHAR(50)[] | NOT NULL, DEFAULT '{}' |
| anti_pattern | TEXT | NOT NULL |
| code_example | TEXT | NULLABLE |
| remediation | TEXT | NOT NULL |
| static_rule_possible | BOOLEAN | NOT NULL, DEFAULT FALSE |
| semgrep_rule_id | VARCHAR(50) | NULLABLE (e.g., 'unsafe-regex-001') |
| embedding | VECTOR(768) | NOT NULL (auto-generated) |
| tags | VARCHAR(100)[] | DEFAULT '{}' |
| version | INTEGER | NOT NULL, DEFAULT 1 (optimistic locking) |
| deleted_at | TIMESTAMPTZ | NULLABLE (soft delete) |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() |
| created_by | UUID | FK → User, NOT NULL |

**RLS**: `(tenant_id = current_setting('app.tenant_id')::uuid OR tenant_id IS NULL) AND deleted_at IS NULL`
**Indexes**: HNSW on `embedding` (vector_cosine_ops), GIN on `tags`, B-tree on `category`, B-tree on `source_url`, full-text on `title, anti_pattern, remediation`.

### SemgrepRule

| Field | Type | Constraints |
|-------|------|-------------|
| id | VARCHAR(50) | PK (e.g., 'unsafe-regex-001') |
| tenant_id | UUID | FK → Tenant, NULLABLE (NULL = public) |
| incident_id | UUID | FK → Incident, NOT NULL |
| category | ENUM (10 categories) | NOT NULL |
| sequence_number | INTEGER | NOT NULL (within category) |
| revision | INTEGER | NOT NULL, DEFAULT 1 |
| yaml_content | TEXT | NOT NULL |
| test_file_content | TEXT | NOT NULL |
| languages | VARCHAR(50)[] | NOT NULL |
| severity | ENUM('error', 'warning', 'info') | NOT NULL |
| message | TEXT | NOT NULL (shown to developer) |
| remediation | TEXT | NOT NULL |
| source | ENUM('manual', 'synthesized') | NOT NULL |
| synthesis_confidence | FLOAT | NULLABLE (for L3 synthesized rules) |
| enabled | BOOLEAN | NOT NULL, DEFAULT TRUE |
| false_positive_count | INTEGER | NOT NULL, DEFAULT 0 |
| auto_disabled | BOOLEAN | NOT NULL, DEFAULT FALSE |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() |
| approved_by | UUID | FK → User, NULLABLE |
| approved_at | TIMESTAMPTZ | NULLABLE |

**RLS**: `(tenant_id = current_setting('app.tenant_id')::uuid OR tenant_id IS NULL)`
**Indexes**: B-tree on `category`, B-tree on `incident_id`.
**Constraint**: UNIQUE(category, sequence_number, tenant_id) for ID generation.
**Invariant — Approval by source**: Rules created from SynthesisCandidate (`source = 'synthesized'`) require explicit admin approval — `approved_by` and `approved_at` are set when the admin approves the candidate. Rules created manually by an admin (`source = 'manual'`) are auto-approved on creation: `approved_by = creator`, `approved_at = created_at`.

### Scan

| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | PK, generated |
| tenant_id | UUID | FK → Tenant, NOT NULL |
| trigger_source | ENUM('github_push', 'github_pr', 'mcp', 'rest_api', 'pre_commit') | NOT NULL |
| repository | VARCHAR(500) | NULLABLE |
| pr_number | INTEGER | NULLABLE |
| commit_sha | VARCHAR(40) | NULLABLE |
| diff_lines | INTEGER | NULLABLE |
| diff_truncated | BOOLEAN | NOT NULL, DEFAULT FALSE |
| risk_level | ENUM('low', 'medium', 'high') | NULLABLE (NULL for L1-only) |
| risk_score | INTEGER | NULLABLE (integer by design — composite formula uses only integer weights and additions, no division or fractional components) |
| llm_model_used | VARCHAR(50) | NULLABLE |
| layer1_findings_count | INTEGER | NOT NULL, DEFAULT 0 |
| layer2_advisories_count | INTEGER | NOT NULL, DEFAULT 0 |
| duration_ms | INTEGER | NOT NULL |
| status | ENUM('running', 'completed', 'failed', 'timeout') | NOT NULL |
| error_message | TEXT | NULLABLE |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() |
| completed_at | TIMESTAMPTZ | NULLABLE |

**RLS**: `tenant_id = current_setting('app.tenant_id')::uuid`
**CHECK**: `risk_level IN ('low', 'medium', 'high') OR risk_level IS NULL` — NULL indicates an L1-only scan (no RAG analysis performed). risk_level is populated only when Layer 2 triage runs.
**Indexes**: B-tree on `(tenant_id, created_at)` for trends, B-tree on `repository`.
**Retention**: Auto-purge per tier (Free 90d, Team 1y, Enterprise 2y) — applies to findings, not scans.

### Finding

| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | PK, generated |
| scan_id | UUID | FK → Scan, NOT NULL |
| tenant_id | UUID | FK → Tenant, NOT NULL |
| rule_id | VARCHAR(50) | FK → SemgrepRule, NOT NULL |
| incident_id | UUID | FK → Incident, NOT NULL |
| file_path | VARCHAR(1000) | NOT NULL |
| start_line | INTEGER | NOT NULL |
| end_line | INTEGER | NOT NULL |
| code_snippet | TEXT | NULLABLE (context only, not full source) |
| severity | ENUM('critical', 'high', 'medium', 'low') | NOT NULL |
| message | TEXT | NOT NULL |
| remediation | TEXT | NOT NULL |
| false_positive_reported | BOOLEAN | NOT NULL, DEFAULT FALSE |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() |

**RLS**: `tenant_id = current_setting('app.tenant_id')::uuid`
**Indexes**: B-tree on `scan_id`, B-tree on `rule_id`.

### Advisory

| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | PK, generated |
| scan_id | UUID | FK → Scan, NOT NULL |
| tenant_id | UUID | FK → Tenant, NOT NULL |
| incident_id | UUID | FK → Incident, NOT NULL |
| confidence_score | FLOAT | NOT NULL (0.0-1.0) |
| risk_level | ENUM('low', 'medium', 'high') | NOT NULL |
| matched_anti_pattern | TEXT | NOT NULL |
| analysis_text | TEXT | NOT NULL (posted as PR comment) |
| llm_model_used | VARCHAR(50) | NOT NULL |
| file_path | VARCHAR(1000) | NULLABLE (set when advisory can be anchored to a specific file in the diff) |
| start_line | INTEGER | NULLABLE (set when advisory can be anchored to a specific line; NULL = top-level PR comment) |
| github_comment_id | BIGINT | NULLABLE |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() |

**RLS**: `tenant_id = current_setting('app.tenant_id')::uuid`

### AuditLogEntry

| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | PK, generated |
| tenant_id | UUID | FK → Tenant, NOT NULL |
| actor_id | UUID | FK → User, NOT NULL |
| entity_type | VARCHAR(50) | NOT NULL (incident, rule, user, tenant) |
| entity_id | VARCHAR(50) | NOT NULL |
| action | ENUM('create', 'update', 'delete', 'soft_delete', 'hard_delete', 'approve', 'disable') | NOT NULL |
| changes | JSONB | NOT NULL (before/after for each changed field) |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() |

**RLS**: `tenant_id = current_setting('app.tenant_id')::uuid`
**Indexes**: B-tree on `(tenant_id, created_at)`, B-tree on `(entity_type, entity_id)`.
**Immutable**: INSERT only, no UPDATE or DELETE allowed (enforced via RLS policy or trigger).

### SynthesisCandidate

| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | PK, generated |
| tenant_id | UUID | FK → Tenant, NOT NULL |
| anti_pattern_hash | VARCHAR(64) | NOT NULL (dedup key) |
| matched_advisory_ids | UUID[] | NOT NULL (the 3+ advisories that triggered synthesis) |
| candidate_yaml | TEXT | NOT NULL |
| candidate_test_file | TEXT | NOT NULL |
| incident_ids | UUID[] | NOT NULL |
| status | ENUM('pending', 'approved', 'rejected', 'archived', 'failed') | NOT NULL, DEFAULT 'pending' |
| failure_reason | TEXT | NULLABLE (populated on transition to 'failed') |
| failure_count | INTEGER | NOT NULL, DEFAULT 0 (incremented on each failed attempt; >= 3 auto-archives) |
| pr_url | VARCHAR(2048) | NULLABLE |
| promoted_rule_id | VARCHAR(50) | NULLABLE (FK → SemgrepRule, set after approval) |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() |
| expires_at | TIMESTAMPTZ | NOT NULL (created_at + 30 days) |
| reviewed_by | UUID | FK → User, NULLABLE |
| reviewed_at | TIMESTAMPTZ | NULLABLE |

**RLS**: `tenant_id = current_setting('app.tenant_id')::uuid`

## Enum Definitions

### incident_category

```text
unsafe-regex, race-condition, missing-error-handling, injection,
resource-exhaustion, missing-safety-check, deployment-error,
data-consistency, unsafe-api-usage, cascading-failure
```

### severity

```text
critical, high, medium, low
```

### plan_tier

```text
free, team, enterprise
```

### user_role

```text
viewer, editor, admin
```

## State Transitions

### Incident Lifecycle

```text
[created] → [active] → [soft_deleted]
                              ↓
                        [hard_deleted] (CLI only, --hard-delete)

Constraint: Cannot transition to soft_deleted if semgrep_rule_id is set and rule is active.
```

### SemgrepRule Lifecycle

```text
[created] → [enabled] ⇄ [disabled] (manual toggle or auto-disable at 3 false positives)
                ↓
          [deprecated] (when incident is deleted or rule is replaced)
```

### SynthesisCandidate Lifecycle

```text
[pending] → [approved] → rule promoted to SemgrepRule
    ↓            ↓
[archived]  [rejected]
    ↑
(auto-archive after 30 days if still pending)
[failed] (if generated rule fails its own test cases)
```
