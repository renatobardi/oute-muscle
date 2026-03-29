# REST API Contract

**Base URL**: `https://muscle.oute.pro/api/v1`
**Auth**: Bearer token (JWT) for dashboard users, API key (`X-API-Key` header) for CI/CD integrations.
**Content-Type**: `application/json` (default), `application/sarif+json` (via `Accept` header)
**Rate Limiting**: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` headers on every response.
**Pagination**: REST API uses `page`/`per_page` for navigable list endpoints. This differs from the MCP Server which uses `max_results` — the divergence is intentional: REST serves browsable UIs, MCP serves single-shot tool calls with bounded results.
**Metering**: REST API does NOT use per-call metering or quota tracking. Cost control is via per-tier rate limiting (FR-023). Per-call metering is exclusive to the MCP channel (FR-024).

## Incidents

### POST /incidents/ingest-url
Ingest an incident from a public post-mortem URL. Returns a draft for review.

**Request**:
```json
{ "url": "https://blog.cloudflare.com/details-of-the-cloudflare-outage-on-july-2-2019" }
```

**Response 200**:
```json
{
  "draft": {
    "title": "Cloudflare outage caused by catastrophic regex backtracking",
    "category": "unsafe-regex",
    "severity": "critical",
    "affected_languages": ["python", "javascript"],
    "anti_pattern": "Regular expression with nested quantifiers causing O(2^n) backtracking",
    "code_example": "pattern = re.compile(r'(?:(?:\\\")+)+')",
    "remediation": "Use atomic groups or possessive quantifiers. Set regex timeout. Use RE2 engine.",
    "static_rule_possible": true,
    "source_url": "https://blog.cloudflare.com/details-of-the-cloudflare-outage-on-july-2-2019",
    "organization": "Cloudflare"
  }
}
```

**Note**: The `organization` field in the draft response is a best-effort extraction by the LLM. It may be null if the post-mortem does not clearly identify the affected organization. This does not fail the ingestion — organization is not a required field.

**Response 409**: `{ "error": "URL already ingested", "incident_id": "..." }`

### POST /incidents
Create an incident (from draft or manual entry).

**Request**:
```json
{
  "title": "string (required)",
  "category": "unsafe-regex | race-condition | ... (required)",
  "severity": "critical | high | medium | low (required)",
  "anti_pattern": "string (required)",
  "remediation": "string (required)",
  "affected_languages": ["python"],
  "code_example": "string (optional)",
  "source_url": "string (optional)",
  "organization": "string (optional)",
  "static_rule_possible": false,
  "tags": ["regex", "dos"]
}
```

**Response 201**: Full incident object with `id`, `embedding` (omitted), `version`, timestamps.

### GET /incidents
List/search incidents. Supports text search and semantic search.

**Query params**:
- `q` (string): Free-text search
- `semantic` (boolean): If true, `q` is used for vector similarity search
- `category` (string): Filter by category
- `severity` (string): Filter by severity
- `page` (int, default 1), `per_page` (int, default 20, max 100)

**Response 200**:
```json
{
  "items": [{ "id": "...", "title": "...", "category": "...", "confidence": 0.92, ... }],
  "total": 150,
  "page": 1,
  "per_page": 20
}
```

### GET /incidents/:id
Get a single incident by ID.

### PUT /incidents/:id
Update an incident. Requires `version` field for optimistic locking.

**Request**: Partial update with `version` field.
**Response 200**: Updated incident.
**Response 409**: `{ "error": "Conflict — incident modified by another user. Reload and retry.", "current_version": 5 }`

### DELETE /incidents/:id
Soft delete an incident.
**Response 409**: `{ "error": "Cannot delete — incident has active linked rule", "rule_id": "unsafe-regex-001" }`

## Rules

### GET /rules
List Semgrep rules (public + tenant-specific).
**Query params**: `category`, `enabled` (boolean), `source` (manual/synthesized), `page`, `per_page`.

### PATCH /rules/:id
Toggle rule enabled/disabled. Admin only.
**Request**: `{ "enabled": false }`

### GET /rules/:id/yaml
Download raw YAML rule content.

### GET /rules/:id/test
Download rule test file content.

## Scans

### POST /scans
Trigger a scan with a diff payload. Used by REST API channel (GitLab, Bitbucket, Jenkins).

**Request**:
```json
{
  "diff": "string (unified diff format)",
  "repository": "org/repo",
  "commit_sha": "abc123",
  "pr_number": 42
}
```

**Response 200**:
```json
{
  "scan_id": "...",
  "findings": [
    {
      "rule_id": "unsafe-regex-001",
      "incident_id": "...",
      "incident_url": "https://...",
      "file_path": "src/utils.py",
      "start_line": 42,
      "end_line": 42,
      "severity": "critical",
      "category": "unsafe-regex",
      "message": "Catastrophic regex backtracking detected",
      "remediation": "Use RE2 or add timeout"
    }
  ],
  "advisories": [],
  "risk_level": "low",
  "duration_ms": 1200
}
```

**Response with `Accept: application/sarif+json`**: Returns SARIF 2.1.0 format.

### GET /scans
List scans for tenant. Query params: `repository`, `status`, `from`, `to`, `page`, `per_page`.

### GET /scans/:id
Get scan details with findings and advisories.

## Tenants & Users

### GET /tenants/me
Get current tenant profile, plan, usage.

### GET /tenants/me/users
List tenant users.

### POST /tenants/me/users/invite
Invite a user. **Request**: `{ "email": "...", "role": "editor" }`

### PATCH /tenants/me/users/:id
Update user role. Admin only.

## Synthesis Candidates (Enterprise)

### GET /synthesis/candidates
List pending synthesis candidates. Admin only.

### POST /synthesis/candidates/:id/approve
Approve a candidate → promote to SemgrepRule.

### POST /synthesis/candidates/:id/reject
Reject a candidate.

## Audit Log (Enterprise)

### GET /audit-log
**Query params**: `entity_type`, `action`, `from`, `to`, `page`, `per_page`.
**Response 200**: Paginated list of audit log entries.

## Error Format

All errors follow:
```json
{
  "error": "Human-readable message",
  "code": "MACHINE_READABLE_CODE",
  "details": {}
}
```

**Standard codes**: `UNAUTHORIZED`, `FORBIDDEN`, `NOT_FOUND`, `CONFLICT`, `RATE_LIMITED`, `QUOTA_EXCEEDED`, `VALIDATION_ERROR`, `PLAN_LIMIT_EXCEEDED`.
