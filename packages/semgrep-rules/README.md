# Semgrep Rules — Oute Muscle

Incident-based static analysis rules. Each rule is traceable to a documented production incident.

## Categories

| Category | Description |
|----------|-------------|
| unsafe-regex | Catastrophic backtracking patterns |
| race-condition | Concurrent access without proper synchronization |
| missing-error-handling | Unhandled exceptions and errors |
| injection | SQL, command, and template injection risks |
| resource-exhaustion | Memory leaks, connection pool exhaustion |
| missing-safety-check | Missing nil checks, bounds checks, auth checks |
| deployment-error | Configuration and deployment anti-patterns |
| data-consistency | Transaction and consistency violations |
| unsafe-api-usage | Deprecated or dangerous API usage |
| cascading-failure | Patterns that cause cascading failures |

## Rule Format

Every rule MUST have:
- `{id}.yaml` — the rule definition with incident metadata
- `{id}.test.py` (or `.test.js`) — positive and negative test cases

## Incident Traceability

Rules MUST include metadata linking to the originating incident:

```yaml
metadata:
  incident_id: "<uuid>"
  incident_url: "<url>"
  severity: "critical|high|medium|low"
  category: "<category>"
  remediation: "<fix description>"
```
