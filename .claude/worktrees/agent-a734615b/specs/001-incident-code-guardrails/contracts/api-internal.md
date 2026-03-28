# Internal API Contracts

Internal interfaces between services within the monorepo. Not exposed to external consumers.

## Core Package Ports (packages/core/src/ports/)

### LLM Port (`llm.py`)

```python
class LLMPort(Protocol):
    async def generate(self, prompt: str, max_tokens: int = 4096) -> LLMResponse: ...
    async def generate_structured(self, prompt: str, schema: type[BaseModel]) -> BaseModel: ...

class LLMResponse:
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
```

**Adapters**: `VertexGeminiFlashAdapter`, `VertexGeminiProAdapter`, `VertexClaudeAdapter`.

### Embedding Port (`embedding.py`)

```python
class EmbeddingPort(Protocol):
    async def embed(self, text: str) -> list[float]: ...
    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...
```

**Adapter**: `VertexEmbeddingAdapter` (text-embedding-005, 768 dimensions).

### Incident Repository Port (`incident_repo.py`)

```python
class IncidentRepoPort(Protocol):
    async def create(self, incident: IncidentCreate) -> Incident: ...
    async def get_by_id(self, id: UUID) -> Incident | None: ...
    async def update(self, id: UUID, data: IncidentUpdate, expected_version: int) -> Incident: ...
    async def soft_delete(self, id: UUID) -> None: ...
    async def hard_delete(self, id: UUID) -> None: ...
    async def search_text(self, query: str, limit: int = 20, offset: int = 0) -> list[Incident]: ...
    async def search_vector(self, embedding: list[float], limit: int = 10) -> list[IncidentMatch]: ...
    async def list_by_category(self, category: str, limit: int = 20, offset: int = 0) -> list[Incident]: ...
```

**Raises**: `OptimisticLockError` on version mismatch, `LinkedRuleError` on delete with active rule.

### Rule Repository Port (`rule_repo.py`)

```python
class RuleRepoPort(Protocol):
    async def create(self, rule: RuleCreate) -> SemgrepRule: ...
    async def get_by_id(self, id: str) -> SemgrepRule | None: ...
    async def list_active(self, category: str | None = None) -> list[SemgrepRule]: ...
    async def toggle_enabled(self, id: str, enabled: bool) -> SemgrepRule: ...
    async def increment_false_positive(self, id: str) -> int: ...
    async def next_sequence_number(self, category: str) -> int: ...
```

### Vector Search Port (`vector_search.py`)

```python
class VectorSearchPort(Protocol):
    async def find_similar(self, embedding: list[float], limit: int = 10, threshold: float = 0.7) -> list[VectorMatch]: ...

class VectorMatch:
    incident_id: UUID
    distance: float
    confidence: float  # 1.0 - distance
```

### GitHub Port (`github.py`)

```python
class GitHubPort(Protocol):
    async def get_pr_diff(self, installation_id: int, owner: str, repo: str, pr_number: int) -> str: ...
    async def create_check_run(self, installation_id: int, owner: str, repo: str, head_sha: str, sarif: dict) -> None: ...
    async def post_review_comment(self, installation_id: int, owner: str, repo: str, pr_number: int, comment: ReviewComment) -> int: ...
    async def create_pr(self, installation_id: int, owner: str, repo: str, title: str, body: str, head: str, base: str) -> str: ...
```

## Risk Score Calculator

```python
def compute_risk_score(
    layer1_findings: int,
    sensitive_paths: list[str],
    diff_lines: int,
    high_risk_categories: list[str],
) -> tuple[int, str]:
    """Returns (score, risk_level).

    Score formula:
      score = (layer1_findings * 3)
            + (sensitive_path_count * 2)
            + (2 if diff_lines > 500 else 0)
            + (high_risk_category_count * 4)

    Thresholds:
      low:    score < 5
      medium: 5 <= score <= 12
      high:   score > 12

    Sensitive paths: infra/, auth/, deploy/, .github/workflows/
    High-risk categories: injection, cascading-failure
    """
```

## Worker Interfaces

### RAG Worker (Cloud Run Job)

**Trigger**: HTTP POST from API after GitHub webhook processing.

**Input**:
```json
{
  "scan_id": "...",
  "tenant_id": "...",
  "diff": "unified diff content",
  "diff_lines": 450,
  "layer1_findings": 2,
  "risk_level": "high",
  "pr_context": {
    "installation_id": 12345,
    "owner": "org",
    "repo": "repo",
    "pr_number": 42
  }
}
```

**Output**: Updates Scan record with advisories; posts PR review comments.

### Synthesis Worker (Cloud Tasks)

**Trigger**: Cloud Tasks queue after RAG advisory detects 3+ matches for same pattern.

**Input**:
```json
{
  "tenant_id": "...",
  "anti_pattern_hash": "sha256...",
  "advisory_ids": ["...", "...", "..."],
  "incident_ids": ["...", "..."]
}
```

**Output**: Creates SynthesisCandidate record; optionally opens PR.

**Failure Workflow**:

A SynthesisCandidate transitions to `failed` status in two cases:

1. **Test failure**: The generated Semgrep rule does not pass its own positive/negative test cases. The worker runs `semgrep --test` on the candidate; if any test assertion fails, the candidate is marked `failed` with `failure_reason` describing which test case failed.

2. **PR creation failure**: Opening the candidate rule PR on GitHub fails after 3 retry attempts with exponential backoff (1min, 5min, 15min). The candidate is marked `failed` with `failure_reason` recording the last error.

**Recovery**: An admin can resend a failed candidate from the dashboard approval queue. On resend:
- Status transitions back to `pending`
- `failure_count` is incremented
- Synthesis worker re-runs rule generation and test validation
- After `failure_count >= 3`, the candidate transitions to `archived` instead of `pending`

**Data model fields** (on SynthesisCandidate):
- `failure_reason`: TEXT, NULLABLE — populated on transition to `failed`
- `failure_count`: INTEGER, NOT NULL, DEFAULT 0 — incremented on each failed attempt
