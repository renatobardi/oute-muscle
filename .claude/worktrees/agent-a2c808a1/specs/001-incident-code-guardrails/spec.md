# Feature Specification: Incident-Based Code Guardrails Platform

**Feature Branch**: `001-incident-code-guardrails`
**Created**: 2026-03-28
**Status**: Draft
**Input**: User description: "Oute Muscle — incident-based code guardrails with 3-layer detection, knowledge base CRUD, multi-tenant delivery via GitHub App, MCP Server, and REST API"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Static Rule Scanning via Pre-Commit and CI (Priority: P1)

A developer pushes code to a repository protected by Oute Muscle. The system runs deterministic Semgrep rules — each derived from a real production incident — as a pre-commit hook (under 2 seconds) and as a blocking GitHub Action in CI. When a match is found, the developer sees the violation with a direct link to the originating incident, the anti-pattern explanation, and the recommended remediation. Output is SARIF-formatted for the GitHub Security Tab.

**Why this priority**: Layer 1 is the foundation of the product. It delivers immediate, deterministic value with zero LLM dependency. Every other layer builds on top of the rule taxonomy and incident metadata established here.

**Independent Test**: Install the GitHub App on a test repository, push a commit containing a known anti-pattern (e.g., catastrophic regex `(.+)+$`), and verify the CI check fails with the correct incident reference and remediation guidance.

**Acceptance Scenarios**:

1. **Given** a repository with the Oute Muscle GitHub App installed and Layer 1 enabled, **When** a developer pushes a commit containing a catastrophic regex pattern, **Then** the CI check fails, the SARIF report appears in the GitHub Security Tab, and the finding includes: rule ID, incident reference URL, severity, category ("unsafe-regex"), and remediation text.
2. **Given** a developer running the pre-commit hook locally, **When** the hook scans a staged file with a missing error handling pattern, **Then** the scan completes in under 2 seconds and outputs the violation with incident context to stderr.
3. **Given** a commit with no matching anti-patterns, **When** the CI check runs, **Then** the check passes with zero findings and completes within the time budget.
4. **Given** a repository with custom tenant-specific rules, **When** a scan runs, **Then** both public rules and tenant-specific rules are evaluated.

---

### User Story 2 — Incident Knowledge Base Management (Priority: P2)

A tech lead or security engineer manages the incident knowledge base that feeds all detection layers. They can ingest incidents from three sources: (a) providing a public post-mortem URL for automatic extraction, (b) filling a manual form in the dashboard, or (c) using the CLI for batch seeding. Every incident record includes structured fields (title, category from 10 predefined categories, anti-pattern, remediation, severity, affected languages) and an automatically generated embedding for vector similarity search. Incidents can be searched by text, ID, or semantic similarity. Editing an incident's anti-pattern automatically regenerates the embedding and optionally propagates changes to linked Semgrep rules. Deletion is soft by default, with hard delete available via CLI for compliance. All mutations are audit-logged.

**Why this priority**: The knowledge base is the core data asset. Without well-structured incident data, neither Layer 1 rules nor Layer 2 advisory can function. This story establishes the data foundation and the operational workflow for growing the knowledge base.

**Independent Test**: Ingest an incident via URL (e.g., a Cloudflare post-mortem), verify the extracted fields are correct, edit the anti-pattern, confirm the embedding is regenerated, and verify the audit log records all changes.

**Acceptance Scenarios**:

1. **Given** a tech lead on the dashboard, **When** they submit a public post-mortem URL, **Then** the system fetches the page, extracts structured fields via LLM, and presents a draft for review before persisting. The URL must not already exist in the knowledge base.
2. **Given** a security engineer on the dashboard, **When** they fill the manual incident form with all required fields (title, category, anti-pattern, remediation), **Then** the incident is saved, an embedding is generated, and if "static_rule_possible" is true, the system suggests Semgrep rule generation.
3. **Given** a CLI user, **When** they run `oute-muscle ingest --file incidents.jsonl --auto-approve`, **Then** each line is parsed, validated, persisted, and embeddings are generated in batch.
4. **Given** an editor editing an incident's anti-pattern field, **When** they save, **Then** the embedding is regenerated and, if a linked Semgrep rule exists, the system prompts: "This incident has an associated rule. Update the rule too?"
5. **Given** an admin attempting to delete an incident that has a linked Semgrep rule, **When** they confirm deletion, **Then** the system blocks the deletion and requires the rule to be unlinked or deleted first.
6. **Given** a viewer-role user, **When** they attempt to edit an incident, **Then** the system denies access and explains the required role.
7. **Given** a search query "retry without backoff", **When** submitted, **Then** the system returns incidents ranked by semantic similarity using vector search, alongside any exact text matches.

---

### User Story 3 — RAG Advisory on Pull Requests (Priority: P3)

When a developer opens a pull request, the system extracts the diff, generates embeddings, and queries the knowledge base for semantically similar past incidents. A triage model classifies the PR as low, medium, or high risk. Low-risk PRs receive a brief advisory summary. Medium-risk PRs receive deeper analysis. High-risk PRs (security changes, architectural changes, patterns matching known incidents) receive maximum-quality analysis. Results are posted as non-blocking review comments on the PR, showing: matched incidents, confidence score, risk level, and recommended actions. The advisory never blocks a merge.

**Why this priority**: Layer 2 is the first LLM-powered differentiation. It catches semantic patterns that static rules cannot express (e.g., "failover without fencing", "retry without exponential backoff") and turns the knowledge base into an active reviewer.

**Independent Test**: Open a PR that introduces a retry loop without exponential backoff on a test repository. Verify the system posts a non-blocking review comment citing the relevant incident(s) with a confidence score above the threshold.

**Acceptance Scenarios**:

1. **Given** a PR with a diff that semantically matches a known incident (retry without backoff), **When** the RAG pipeline runs, **Then** a non-blocking review comment is posted with: matched incident title, source URL, confidence score, risk level, and recommended remediation.
2. **Given** a low-risk PR (routine refactor, no matching incidents), **When** triage completes, **Then** the system posts a brief "no relevant incidents found" summary or no comment at all (configurable per tenant).
3. **Given** a high-risk PR flagged by triage, **When** deep analysis completes, **Then** the review comment includes a detailed explanation of the risk, matching incidents with confidence scores, and specific code locations in the diff that triggered the match.
4. **Given** a PR on a repository where Layer 2 is not enabled (Free tier), **When** a PR is opened, **Then** only Layer 1 static scanning runs; no RAG advisory is triggered.
5. **Given** the advisory system is unavailable (LLM timeout, service outage), **When** a PR is opened, **Then** the PR is not blocked, a degraded-mode notice is posted, and the incident is logged for retry.

---

### User Story 4 — Automatic Rule Synthesis (Priority: P4)

When the RAG advisory flags the same code pattern across 3 or more pull requests with high confidence, the system automatically triggers rule synthesis. An LLM generates a candidate Semgrep rule with positive and negative test cases. The candidate rule is opened as a pull request in the tenant's rule repository for human review. Upon approval and merge, the rule is promoted to Layer 1 and becomes a blocking check in CI.

**Why this priority**: Layer 3 closes the feedback loop — the system learns and hardens over time. Per the Incremental Complexity principle, this layer is built only after Layer 2 is proven in production.

**Independent Test**: Simulate 3 PRs flagged by RAG for the same pattern, verify a candidate rule PR is created with valid Semgrep YAML and test cases, approve and merge it, then confirm the rule appears in Layer 1 scans.

**Acceptance Scenarios**:

1. **Given** the RAG system has flagged the same anti-pattern in 3 separate PRs with confidence above the threshold, **When** the synthesis pipeline runs, **Then** a candidate Semgrep rule is generated with: YAML rule definition, positive test case (code that should match), negative test case (code that should not match), and incident references.
2. **Given** a candidate rule PR is opened, **When** an admin reviews and merges it, **Then** the rule is added to Layer 1 and enforced on subsequent scans.
3. **Given** a candidate rule that fails its own test cases, **When** synthesis completes, **Then** the system does not open a PR and logs the failure for investigation.
4. **Given** a Free-tier tenant, **When** synthesis conditions are met, **Then** synthesis does not trigger (Enterprise-only feature).

---

### User Story 5 — MCP Server for IDE Integration (Priority: P5)

A developer using an IDE with MCP support (Cursor, Windsurf, Claude Desktop, VS Code Copilot) connects to the Oute Muscle MCP Server via Streamable HTTP with OAuth 2.1 authentication. The server exposes 5 tools: `scan_code` (run Layer 1 rules on a code snippet), `get_incident_advisory` (query knowledge base for a code pattern), `synthesize_rules` (request rule generation from an incident), `list_relevant_incidents` (search by text or semantic similarity), and `validate_fix` (check if a proposed fix resolves a flagged finding). Each tool returns structured JSON. Usage is metered: 50 free scans/month, then pay-as-you-go.

**Why this priority**: MCP is an emerging distribution channel that reaches developers directly in their workflow, but is secondary to the GitHub App integration which covers CI/CD.

**Independent Test**: Connect to the MCP Server from a test client, authenticate via OAuth 2.1, call `scan_code` with a known anti-pattern, and verify the response includes the matching rule and incident reference.

**Acceptance Scenarios**:

1. **Given** a developer authenticated via OAuth 2.1, **When** they call `scan_code` with a code snippet containing a catastrophic regex, **Then** the response includes the matching rule ID, incident reference, severity, and remediation.
2. **Given** a developer, **When** they call `list_relevant_incidents` with "circuit breaker missing", **Then** the response includes semantically similar incidents ranked by confidence.
3. **Given** a developer who has used 50 free scans this month, **When** they call any tool, **Then** the response indicates the free quota is exhausted and provides upgrade/payment options.
4. **Given** an unauthenticated request, **When** any tool is called, **Then** the server returns a 401 with an OAuth 2.1 authorization URL.

---

### User Story 6 — REST API for Generic CI/CD Integration (Priority: P6)

Teams using GitLab, Bitbucket, or Jenkins integrate with Oute Muscle via a REST API that accepts webhook payloads with diff content. The API provides the same Layer 1 scanning and Layer 2 advisory as the GitHub App, returning findings in a standardized JSON format. Authentication is via API key scoped to the tenant. The API supports SARIF output for tools that consume it.

**Why this priority**: Expands market beyond GitHub-only teams, but is a secondary channel to the GitHub App.

**Independent Test**: Send a webhook payload with a diff containing a known anti-pattern to the REST API, verify the response includes findings in both JSON and SARIF formats.

**Acceptance Scenarios**:

1. **Given** a valid API key for a Team-tier tenant, **When** a webhook payload with a diff is sent to the scan endpoint, **Then** the response includes Layer 1 findings in JSON format with incident references.
2. **Given** a request with `Accept: application/sarif+json`, **When** findings exist, **Then** the response is valid SARIF 2.1.0.
3. **Given** an invalid or expired API key, **When** any endpoint is called, **Then** the server returns 401 with a clear error message.
4. **Given** a Free-tier API key, **When** a scan is requested, **Then** only Layer 1 public rules are applied (no RAG advisory).

---

### User Story 7 — Multi-Tenant Dashboard and Configuration Portal (Priority: P7)

An engineering manager or admin accesses the Oute Muscle dashboard to: view scan results and trends across repositories, configure which rules are active, manage the tenant's private incident knowledge base, review and approve synthesized rules, manage team members and roles (viewer, editor, admin), and view billing/usage metrics. Enterprise tenants additionally access SSO/SAML configuration and audit logs.

**Why this priority**: The dashboard is essential for ongoing operations but is not required for the core detection value, which is delivered through CI/CD and IDE integrations.

**Independent Test**: Log in as an admin, view scan results for a repository, toggle a rule on/off, add a team member with editor role, and verify changes are reflected in the next scan.

**Acceptance Scenarios**:

1. **Given** an admin logged into the dashboard, **When** they navigate to the rules page, **Then** they see all active rules (public + tenant-specific), can enable/disable individual rules, and see the linked incident for each rule.
2. **Given** an admin, **When** they invite a new team member with "editor" role, **Then** the invited user receives an email, and upon acceptance, can add and edit tenant-specific incidents but cannot modify public incidents.
3. **Given** an Enterprise admin, **When** they navigate to the audit log, **Then** they see a chronological log of all mutations (incident edits, rule changes, role changes) with who, when, and what changed.
4. **Given** a viewer-role user, **When** they attempt to toggle a rule, **Then** the action is denied with a message explaining the required permission.

---

### Edge Cases

- What happens when a post-mortem URL returns a 404 or non-HTML content during ingestion? System retries once, then reports the failure with the HTTP status code and suggests manual entry.
- What happens when two tenants ingest the same public post-mortem URL? The incident is stored once in the shared knowledge base; duplicate detection prevents re-ingestion. Tenant-specific annotations are stored separately via RLS.
- What happens when the LLM service is unavailable during Layer 2 advisory? The PR is not blocked. A degraded-mode comment is posted, and the advisory is queued for retry. Layer 1 static scanning continues independently.
- What happens when a Semgrep rule generates false positives? Users can report false positives via the PR comment. After a configurable threshold (default: 3 reports), the rule is auto-disabled for that tenant and flagged for review.
- What happens when an incident is deleted but its rule is still active? Deletion is blocked until the rule is unlinked or deleted. This is enforced at the data layer.
- What happens when a tenant exceeds their plan limits (contributors, repos)? New scans return a 402 response with a clear upgrade prompt. Existing scan results remain accessible.
- What happens when the MCP free quota is exhausted mid-session? The current tool call returns the result plus a quota warning. The next call returns a quota-exceeded error with upgrade instructions.
- What happens when batch ingestion via CLI contains invalid records? Valid records are persisted; invalid records are skipped and reported in a summary with line numbers and validation errors.
- What happens when two editors save the same incident concurrently? The second save is rejected via optimistic locking ("This incident was modified by another user. Please reload and retry."). No data is lost; the user reloads the current version and re-applies their changes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST run Semgrep rules derived from documented production incidents as a pre-commit hook completing in under 2 seconds for up to 500 changed lines.
- **FR-002**: System MUST run the same Semgrep rules as a blocking GitHub Action in CI, producing SARIF 2.1.0 output for the GitHub Security Tab.
- **FR-003**: Every Semgrep rule MUST contain metadata linking to the originating incident: incident ID, source URL, severity, category, and remediation text.
- **FR-004**: System MUST support 10 predefined incident categories: unsafe-regex, race-condition, missing-error-handling, injection, resource-exhaustion, missing-safety-check, deployment-error, data-consistency, unsafe-api-usage, cascading-failure.
- **FR-005**: System MUST support rule coverage for: Python, JavaScript/TypeScript, HCL/Terraform, YAML, JSON.
- **FR-006**: System MUST ingest incidents from a public URL by fetching the page content and extracting structured fields via LLM, presenting a draft for human review before persisting.
- **FR-007**: System MUST ingest incidents via a manual form in the dashboard with required fields: title, category, anti-pattern, remediation.
- **FR-008**: System MUST ingest incidents via CLI supporting single URL (`--url`), single file (`--file <json>`), and batch file (`--file <jsonl>`), with `--auto-approve` and `--dry-run` flags.
- **FR-009**: System MUST automatically generate an embedding (VECTOR(768)) for each incident's anti-pattern upon creation or update.
- **FR-010**: System MUST support incident search by ID, title text, free text, and semantic similarity via vector search.
- **FR-011**: System MUST enforce soft delete by default for incidents, with hard delete available only via CLI with `--hard-delete` flag.
- **FR-012**: System MUST block deletion of an incident that has a linked Semgrep rule until the rule is unlinked or deleted.
- **FR-013**: System MUST maintain an audit log for all incident mutations recording: user (created_by / actor user_id), timestamp, and changed fields with before/after values. The created_by field is mandatory on every incident and feeds the audit trail.
- **FR-014**: System MUST enforce role-based access: viewer (read-only), editor (add/edit tenant-specific incidents), admin (full access including public incidents and rule approval).
- **FR-015**: System MUST classify each PR as low, medium, or high risk during Layer 2 triage within 1 second of receiving the diff. This is a hard deadline — the composite risk score is computed locally without LLM calls (see FR-017), so sub-second is expected. Diffs exceeding 3,000 lines MUST be truncated to the first 3,000 lines, and the advisory MUST include a warning: "partial analysis — diff truncated at 3,000 lines".
- **FR-016**: System MUST post non-blocking review comments on PRs using a structured markdown template with sections: severity badge (critical/high/medium/low), finding description, matched incident title and source URL, confidence score, risk level, and recommended remediation. Each finding is a separate comment anchored to the relevant code line.
- **FR-017**: System MUST route LLM requests by risk level using a composite score based on: (1) number of Layer 1 findings, (2) files in sensitive paths (infra/, auth/, deploy/), (3) diff size (>500 lines increases risk), (4) high-risk categories matched (injection, cascading-failure). Low-risk routes to fast triage, medium-risk to deeper analysis, high-risk to maximum-quality analysis.
- **FR-018**: System MUST trigger automatic rule synthesis when the same anti-pattern is flagged by RAG in 3 or more PRs with high confidence.
- **FR-019**: System MUST generate candidate Semgrep rules with positive and negative test cases during synthesis, opened as a PR for human review.
- **FR-020**: System MUST expose an MCP Server with Streamable HTTP transport and OAuth 2.1 authentication, providing 5 tools: scan_code, get_incident_advisory, synthesize_rules, list_relevant_incidents, validate_fix.
- **FR-021**: System MUST expose a REST API accepting webhook payloads with diff content, returning findings in JSON and SARIF formats, authenticated via tenant-scoped API key.
- **FR-022**: System MUST enforce multi-tenancy via row-level security, isolating tenant-specific incidents and rules while sharing the public knowledge base.
- **FR-023**: System MUST enforce plan limits: Free (5 contributors, 3 repos, Layer 1 only), Team (unlimited, L1+L2), Enterprise (L1+L2+L3, SSO/SAML, audit logs). Rate limits per tier: Free 30 req/min, Team 120 req/min, Enterprise 600 req/min with burst allowance up to 2x for 10 seconds.
- **FR-024**: System MUST meter MCP tool usage: 50 free scans/month, then pay-as-you-go billing.
- **FR-025**: System MUST provide a dashboard for: viewing scan results/trends, configuring active rules, managing incidents, reviewing synthesized rules, managing team roles, and viewing billing/usage.
- **FR-026**: System MUST seed the knowledge base with 50-80 incidents from public post-mortem databases (danluu/post-mortems, VOID).
- **FR-027**: System MUST never store customer source code at rest — only findings metadata and diff embeddings.
- **FR-028**: System MUST support false positive reporting via PR comments, with auto-disable after a configurable threshold (default: 3 reports per rule per tenant).
- **FR-029**: System MUST retain findings metadata for: Free 90 days, Team 1 year, Enterprise 2 years. Expired findings are purged automatically via scheduled job.
- **FR-030**: System MUST authenticate MCP Server users via OAuth 2.1 Authorization Code with PKCE flow, using the platform's own authorization server. Access tokens expire after 1 hour; refresh tokens expire after 30 days. Token validation is performed locally via signed JWT verification.
- **FR-031**: When incident ingestion via URL determines a Semgrep rule is possible, the candidate rule MUST appear in the admin's approval queue in the dashboard. Approval requires an admin-role user. Unapproved candidates are auto-archived after 30 days with a notification to the tenant admin.
- **FR-032**: Soft-deleted incidents MUST remain in the database indefinitely by default. Automatic hard delete is never triggered — hard delete is only available via explicit CLI command with `--hard-delete` flag for compliance/GDPR purposes.

### Key Entities

- **Incident**: A documented production incident with structured fields (title, category, anti-pattern, remediation, severity, affected languages, embedding) traceable to a source URL. The core data unit feeding all detection layers. Includes a `version` field for optimistic locking — concurrent edits are rejected with "This incident was modified by another user. Please reload and retry."
- **Semgrep Rule**: A deterministic YAML-based detection rule derived from one or more incidents, with mandatory positive/negative test cases. Can be public (shared) or tenant-specific. Identified by `{category}-{NNN}` (e.g., `unsafe-regex-001`, `cascading-failure-012`), with an internal revision field that increments on edits without changing the rule ID.
- **Tenant**: An organization using the platform, with a plan tier, contributor/repo limits, isolated data via RLS, and configurable preferences (active rules, notification settings).
- **User**: A person within a tenant with a role (viewer, editor, admin) governing their permissions across the system.
- **Finding**: A single detection result produced by a scan — links a rule or advisory match to a specific code location, incident reference, and remediation.
- **Advisory**: A Layer 2 RAG result posted as a PR review comment, linking a code pattern to semantically similar incidents with confidence scores.
- **Scan**: An execution of Layer 1 (and optionally Layer 2) against a code diff or snippet, recording: trigger source, findings, timing, and billing event.
- **Audit Log Entry**: An immutable record of a mutation (incident, rule, role change) with who, when, what changed, and before/after values.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Pre-commit hook scans complete in under 2 seconds for files with up to 500 changed lines.
- **SC-002**: CI scans complete within the overall CI pipeline without adding more than 30 seconds to the total run time.
- **SC-003**: At least 50 curated incidents are available in the shared knowledge base at launch, covering all 10 categories.
- **SC-004**: Layer 2 RAG triage classifies PR risk level in under 3 seconds from webhook receipt to risk classification.
- **SC-005**: False positive rate for Layer 1 rules is below 5% as measured by user-reported false positives over total findings in the first 90 days.
- **SC-006**: 90% of users can successfully ingest an incident from a URL in under 3 minutes (from paste URL to confirmed record).
- **SC-007**: Incident search returns relevant results (semantic or text) in under 2 seconds for knowledge bases with up to 10,000 incidents.
- **SC-008**: MCP tool calls return results in under 5 seconds for scan_code and list_relevant_incidents.
- **SC-009**: System supports 100 concurrent tenants, each with up to 50 contributors, without performance degradation.
- **SC-010**: Every finding displayed to a user includes a traceable link to the originating incident — 100% traceability.

## Clarifications

### Session 2026-03-28

- Q: What concrete signals classify a PR as low/medium/high risk for LLM routing? → A: Composite score based on (1) number of Layer 1 findings, (2) files in sensitive paths (infra/, auth/, deploy/), (3) diff size (>500 lines = +risk), (4) high-risk categories matched (injection, cascading-failure).
- Q: What are the concrete rate limits per tier? → A: Free 30 req/min, Team 120 req/min, Enterprise 600 req/min, with burst allowance up to 2x for 10 seconds.
- Q: What is the max diff size for RAG processing and what happens when exceeded? → A: 3,000-line limit; truncate to first 3,000 lines with advisory warning "partial analysis — diff truncated at 3,000 lines".
- Q: What versioning scheme for Semgrep rules? → A: Category-prefixed sequential ID `{category}-{NNN}` (e.g., `unsafe-regex-001`). Edits increment an internal revision field without changing the rule ID.
- Q: What happens with concurrent edits on the same incident? → A: Optimistic locking via `version` field. Second save is rejected; user must reload and retry.

## Assumptions

- Developers have GitHub repositories as their primary source control platform for the P1 use case; GitLab/Bitbucket are secondary channels covered by the REST API.
- Public post-mortem URLs are accessible without authentication and return parseable HTML content.
- The 10 incident categories cover the vast majority of production incidents relevant to code-level detection; the taxonomy may expand in future iterations but is fixed for v1.
- OAuth 2.1 is sufficient for MCP Server authentication; no additional proprietary auth schemes are needed.
- The initial seed of 50-80 incidents from public databases provides sufficient coverage for an effective Layer 1 at launch.
- SSO/SAML integration is an Enterprise-only requirement and is not needed for initial launch of Free and Team tiers.
- Billing and payment processing will integrate with an existing payment provider (e.g., Stripe); the billing system itself is not in scope for this feature spec beyond metering and plan enforcement.
- The pre-commit hook is distributed as a standalone binary or script that runs Semgrep rules locally, without requiring network access to the Oute Muscle backend.
