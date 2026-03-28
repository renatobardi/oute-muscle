# Quickstart: Incident-Based Code Guardrails Platform

**Branch**: `001-incident-code-guardrails` | **Date**: 2026-03-28

## Scenario 1: Layer 1 — Static Scan Catches Catastrophic Regex (P1)

**Goal**: Verify that a known anti-pattern is detected by Semgrep rules in both pre-commit and CI.

**Steps**:
1. Create a test repository with the Oute Muscle GitHub App installed.
2. Create a Python file with a catastrophic regex:
   ```python
   import re
   pattern = re.compile(r'(?:(?:\")+)+')
   ```
3. Stage and attempt to commit.
4. **Expected**: Pre-commit hook runs Semgrep, detects `unsafe-regex-001`, blocks commit with:
   ```
   unsafe-regex-001: Catastrophic regex backtracking [critical]
   Incident: https://blog.cloudflare.com/details-of-the-cloudflare-outage-on-july-2-2019
   Remediation: Use RE2 or bounded quantifiers. Set regex timeout.
   ```
5. Push (bypassing hook) and open a PR.
6. **Expected**: CI GitHub Action runs same rules, check fails, SARIF appears in Security Tab.

**Validates**: FR-001, FR-002, FR-003, SC-001, SC-002.

## Scenario 2: Incident Ingestion from URL (P2)

**Goal**: Ingest a real post-mortem and verify the knowledge base entry.

**Steps**:
1. Log into dashboard as editor.
2. Navigate to Incidents → Ingest from URL.
3. Paste: `https://blog.cloudflare.com/details-of-the-cloudflare-outage-on-july-2-2019`
4. **Expected**: System fetches page, extracts fields:
   - Title: "Cloudflare outage caused by catastrophic regex backtracking"
   - Category: unsafe-regex
   - Severity: critical
   - Anti-pattern: "Regular expression with nested quantifiers..."
   - Remediation: "Use RE2 engine or bounded quantifiers"
5. Review draft, adjust if needed, confirm.
6. **Expected**: Incident saved, embedding generated, appears in search.
7. Search for "regex backtracking".
8. **Expected**: The incident appears as top result (semantic + text match).

**Validates**: FR-006, FR-009, FR-010, SC-006.

## Scenario 3: RAG Advisory on PR (P3)

**Goal**: Verify that Layer 2 posts a non-blocking advisory for a semantically matching pattern.

**Steps**:
1. Ensure knowledge base contains incident about "retry without exponential backoff".
2. Open a PR with:
   ```python
   def call_api(url):
       for attempt in range(10):
           try:
               return requests.get(url)
           except Exception:
               time.sleep(1)  # Fixed delay retry
   ```
3. **Expected within 3 seconds**: Risk triage classifies as medium/high.
4. **Expected**: Non-blocking review comment posted:
   ```
   ⚠️ High Risk — Incident Advisory
   Matched Incident: AWS S3 outage amplified by retry storms
   Confidence: 0.87
   Finding: Fixed-delay retry without exponential backoff...
   Recommended Action: Add exponential backoff with jitter
   ```
5. PR is NOT blocked — merge button remains enabled.

**Validates**: FR-015, FR-016, FR-017, SC-004.

## Scenario 4: MCP Server — scan_code Tool (P5)

**Goal**: Verify MCP tool call via IDE integration.

**Steps**:
1. Configure MCP client (e.g., test harness) with OAuth 2.1 credentials.
2. Authenticate: receive JWT access token.
3. Call `scan_code`:
   ```json
   {
     "code": "import re\npattern = re.compile(r'(?:(?:\\\")+)+')",
     "language": "python",
     "filename": "utils.py"
   }
   ```
4. **Expected**: Response includes finding for `unsafe-regex-001` with incident reference.
5. Check `quota_remaining` is decremented.
6. Call `validate_fix` with a corrected regex.
7. **Expected**: Response says fix is valid, no matching rules.

**Validates**: FR-020, FR-030, SC-008.

## Scenario 5: Batch Ingestion via CLI (P2)

**Goal**: Seed knowledge base with multiple incidents from JSONL file.

**Steps**:
1. Prepare `incidents.jsonl` with 5 incident records.
2. Run: `oute-muscle ingest --file incidents.jsonl --dry-run`
3. **Expected**: Shows what would be ingested without persisting.
4. Run: `oute-muscle ingest --file incidents.jsonl --auto-approve`
5. **Expected**: 5 incidents created, embeddings generated, summary output:
   ```
   Ingested: 5/5 | Skipped: 0 | Errors: 0
   ```
6. Run again with same file.
7. **Expected**: 0 ingested (duplicate URLs detected), 5 skipped.

**Validates**: FR-008, FR-026.

## Scenario 6: Role-Based Access Control (P2/P7)

**Goal**: Verify viewer cannot edit, editor can edit tenant incidents, admin can edit public.

**Steps**:
1. As admin: create a tenant-specific incident.
2. Switch to viewer role: attempt to edit → **Expected**: 403 Forbidden.
3. Switch to editor role: edit the incident → **Expected**: Success, audit log entry created.
4. As editor: attempt to edit a public/shared incident → **Expected**: 403 Forbidden.
5. As admin: edit the public incident → **Expected**: Success.
6. Check audit log: all mutations recorded with who, when, what changed.

**Validates**: FR-014, FR-013.

## Scenario 7: Optimistic Locking (P2)

**Goal**: Verify concurrent edit detection.

**Steps**:
1. Load incident (version=1) in two browser tabs.
2. In tab 1: edit anti_pattern, save → **Expected**: Success, version=2.
3. In tab 2: edit remediation, save with version=1 → **Expected**: 409 Conflict with message "This incident was modified by another user. Please reload and retry."
4. In tab 2: reload → **Expected**: Shows version=2 with tab 1's changes.

**Validates**: FR-013 (audit log), data-model optimistic locking.

## Scenario 8: Rate Limiting (All tiers)

**Goal**: Verify per-tier rate limits are enforced.

**Steps**:
1. As Free-tier tenant, send 31 requests in 1 minute.
2. **Expected**: Request 31 returns 429 with `Retry-After` header.
3. Check response headers: `X-RateLimit-Limit: 30`, `X-RateLimit-Remaining: 0`.
4. Wait for rate window reset, send again → **Expected**: Success.

**Validates**: FR-023.
