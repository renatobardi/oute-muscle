# MCP Server Tools Contract

**Transport**: Streamable HTTP
**Auth**: OAuth 2.1 Authorization Code + PKCE
**Base URL**: `https://mcp.muscle.oute.pro`
**Metering**: 50 free tool calls/month, then pay-as-you-go (FR-024). This is MCP-specific — the REST API uses per-tier rate limiting instead.
**Result Limiting**: MCP tools use `max_results` for bounded single-shot responses. This differs from the REST API which uses `page`/`per_page` pagination — the divergence is intentional: MCP serves tool calls with bounded output, REST serves browsable UIs.

## OAuth 2.1 Flow

1. Client (IDE) redirects to: `GET /oauth/authorize?response_type=code&client_id=...&code_challenge=...&code_challenge_method=S256&redirect_uri=...&scope=scan:read incidents:read`
2. User authenticates (GitHub OAuth or email/password).
3. Callback: `GET /oauth/callback?code=...&state=...`
4. Token exchange: `POST /oauth/token` with `grant_type=authorization_code`.
5. Response: `{ "access_token": "jwt...", "token_type": "bearer", "expires_in": 3600, "refresh_token": "opaque..." }`
6. Refresh: `POST /oauth/token` with `grant_type=refresh_token`.

**Access token**: RS256 JWT, 1h expiry. Claims: `sub` (user_id), `tid` (tenant_id), `role`, `exp`, `iat`.
**Refresh token**: Opaque, 30d expiry, stored hashed in DB. Single-use (rotation on refresh).

## Tools

### scan_code

Scan a code snippet against Layer 1 Semgrep rules.

**Input**:
```json
{
  "code": "import re\npattern = re.compile(r'(?:(?:\\\")+)+')",
  "language": "python",
  "filename": "utils.py"
}
```

**Output**:
```json
{
  "findings": [
    {
      "rule_id": "unsafe-regex-001",
      "incident_id": "...",
      "incident_url": "https://...",
      "severity": "critical",
      "category": "unsafe-regex",
      "line": 2,
      "message": "Catastrophic regex backtracking detected",
      "remediation": "Use RE2 or add timeout"
    }
  ],
  "scan_duration_ms": 450,
  "quota_remaining": 47
}
```

### get_incident_advisory

Query the knowledge base for advisory on a code pattern (Layer 2).

**Input**:
```json
{
  "code": "def retry(fn, max_retries=10):\n    for i in range(max_retries):\n        try: return fn()\n        except: time.sleep(1)",
  "context": "Retry logic for API calls"
}
```

**Output**:
```json
{
  "advisories": [
    {
      "incident_id": "...",
      "incident_title": "AWS S3 outage amplified by retry storms",
      "incident_url": "https://...",
      "confidence": 0.87,
      "risk_level": "high",
      "matched_pattern": "Fixed-delay retry without exponential backoff",
      "recommendation": "Add exponential backoff with jitter: delay = base * 2^attempt + random(0, base)"
    }
  ],
  "quota_remaining": 46
}
```

### list_relevant_incidents

Search incidents by text or semantic similarity.

**Input**:
```json
{
  "query": "circuit breaker missing in microservice calls",
  "max_results": 5
}
```

**Output**:
```json
{
  "incidents": [
    {
      "id": "...",
      "title": "Netflix cascading failure from missing circuit breakers",
      "category": "cascading-failure",
      "severity": "critical",
      "confidence": 0.91,
      "anti_pattern": "Direct service calls without circuit breaker pattern",
      "remediation": "Implement circuit breaker with fallback"
    }
  ],
  "quota_remaining": 45
}
```

### synthesize_rules

Request rule generation from an incident description (Enterprise only).

**Input**:
```json
{
  "incident_id": "...",
  "target_language": "python"
}
```

**Output**:
```json
{
  "candidate_id": "...",
  "status": "pending",
  "yaml_preview": "rules:\n  - id: ...\n    pattern: ...",
  "message": "Candidate rule created. An admin must approve it before it becomes active.",
  "quota_remaining": 44
}
```

**Error 403**: `{ "error": "Rule synthesis requires Enterprise tier" }`

### validate_fix

Check if a proposed fix resolves a previously flagged finding.

**Input**:
```json
{
  "original_code": "pattern = re.compile(r'(?:(?:\\\")+)+')",
  "fixed_code": "pattern = re.compile(r'(?:\\\"){1,100}')",
  "rule_id": "unsafe-regex-001",
  "language": "python"
}
```

**Output**:
```json
{
  "valid": true,
  "message": "Fix resolves the finding. The new pattern uses bounded quantification.",
  "still_matching_rules": [],
  "quota_remaining": 43
}
```

## Error Responses

```json
{
  "error": "Quota exceeded. 50 free scans/month used.",
  "code": "QUOTA_EXCEEDED",
  "upgrade_url": "https://app.muscle.oute.pro/settings/billing"
}
```

**Standard codes**: `UNAUTHORIZED`, `QUOTA_EXCEEDED`, `PLAN_LIMIT_EXCEEDED`, `RATE_LIMITED`, `INTERNAL_ERROR`.

## Quota Headers

Every response includes:
- `X-Quota-Remaining`: Number of free tool calls remaining this month.
- `X-Quota-Reset`: ISO 8601 timestamp of monthly quota reset.
