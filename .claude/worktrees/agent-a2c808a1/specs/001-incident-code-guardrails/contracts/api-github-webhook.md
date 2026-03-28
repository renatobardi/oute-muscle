# GitHub Webhook Contract

**Endpoint**: `POST /webhooks/github`
**Auth**: HMAC-SHA256 signature verification via `X-Hub-Signature-256` header.
**Secret**: Stored in GCP Secret Manager, set during GitHub App installation.

## Supported Events

### pull_request.opened / pull_request.synchronize

Triggers Layer 1 scan + Layer 2 RAG advisory (if tier allows).

**Flow**:
1. Verify HMAC-SHA256 signature.
2. Extract `installation.id` → resolve tenant.
3. Fetch PR diff via GitHub API (`GET /repos/:owner/:repo/pulls/:number` with `Accept: application/vnd.github.diff`).
4. Run Layer 1 (Semgrep scan on diff).
5. If tier includes L2: compute risk score, route to LLM, run RAG advisory.
6. Post results:
   - Layer 1: Create Check Run with SARIF annotations via Checks API.
   - Layer 2: Post review comments via Pull Request Reviews API (non-blocking).
7. Return `202 Accepted` immediately; processing is async via Cloud Run Job.

**Response**: `202 Accepted` with `{ "scan_id": "..." }`.

### push

Triggers Layer 1 scan only (for SARIF upload to Security Tab).

**Flow**:
1. Verify HMAC-SHA256 signature.
2. Extract `installation.id` → resolve tenant.
3. Fetch changed files via GitHub API.
4. Run Semgrep scan.
5. Upload SARIF via `POST /repos/:owner/:repo/code-scanning/sarifs`.
6. Return `202 Accepted`.

### installation.created / installation.deleted

Tenant provisioning and deprovisioning.

**Flow (created)**:
1. Create or link tenant record.
2. Store `installation_id`.
3. Sync repository list.

**Flow (deleted)**:
1. Mark tenant's GitHub integration as disconnected.
2. Do not delete tenant data (they may reconnect or use other channels).

## Check Run Format (Layer 1)

```json
{
  "name": "Oute Muscle — Incident Guardrails",
  "head_sha": "abc123",
  "status": "completed",
  "conclusion": "failure",
  "output": {
    "title": "2 incident-based findings detected",
    "summary": "Found patterns matching known production incidents.",
    "annotations": [
      {
        "path": "src/utils.py",
        "start_line": 42,
        "end_line": 42,
        "annotation_level": "failure",
        "title": "unsafe-regex-001: Catastrophic regex backtracking",
        "message": "This pattern matches incident INC-2019-CF-001 (Cloudflare outage). Use RE2 or add timeout.\n\nIncident: https://blog.cloudflare.com/...\nCategory: unsafe-regex\nSeverity: critical"
      }
    ]
  }
}
```

## PR Review Comment Format (Layer 2)

```markdown
### ⚠️ High Risk — Incident Advisory

**Risk Level**: 🔴 High (score: 14)
**Matched Incident**: [Cloudflare regex outage (2019)](https://blog.cloudflare.com/...)
**Confidence**: 0.89
**Category**: unsafe-regex

**Finding**: This code introduces a regex pattern with nested quantifiers that could cause catastrophic backtracking under adversarial input, similar to the pattern that caused a 27-minute global outage at Cloudflare.

**Recommended Action**: Replace with a linear-time regex using RE2 engine, or add a timeout wrapper.

---
*Oute Muscle — Layer 2 Advisory (non-blocking) | [View incident details](https://app.outemuscle.com/incidents/...)*
```

**Anchoring strategy**: Layer 2 advisories are posted as inline PR review comments when the matched pattern can be tied to a specific file and line range in the diff (using `file_path` + `start_line`). When the advisory is a general observation not tied to a specific line (e.g., architectural concern across multiple files), it is posted as a top-level PR comment instead.

## Webhook Security

- **Signature verification**: `HMAC-SHA256(secret, body)` must match `X-Hub-Signature-256` header.
- **Replay protection**: Reject webhooks older than 5 minutes (compare `X-GitHub-Delivery` timestamp).
- **IP allowlist**: Optional — GitHub webhook IP ranges from `api.github.com/meta`.
