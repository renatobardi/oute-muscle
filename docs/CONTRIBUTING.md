# Contributing

## Development setup

```bash
git clone https://github.com/renatobardi/oute-muscle.git
cd oute-muscle
bash scripts/dev-setup.sh
```

The setup script checks prerequisites (uv, node, gcloud), installs all dependencies, and configures pre-commit hooks.

## Workflow

This project uses a sequential branch naming scheme (`NNN-short-description`) and Gitflow-style rules:

1. **Create a branch** — pick the next number (`git branch --list | sort -r | head -1`)
2. **Write tests first** — TDD is mandatory, not optional
3. **Push and open a PR** — CI must be green before merge
4. **Merge to main** — staging deploys automatically
5. **Tag for prod** — `git tag vX.Y.Z && git push origin vX.Y.Z`

### Branch naming

```
001-initial-setup
002-incidents-crud
003-semgrep-integration
...
NNN-short-description
```

### Commit messages

Conventional Commits are required:

```
feat(incidents): add category filter to list endpoint
fix(auth): handle expired JWT without 500 error
docs(api): add response examples to scan endpoints
chore(deps): bump fastapi to 0.115.0
refactor(core): extract embedding logic to adapter
test(rules): add test for unsafe-regex-003
```

**Scopes**: `api`, `web`, `core`, `db`, `rules`, `infra`, `ci`, `docs`, `deps`

## Code standards

### Python

- Line length: 100 characters
- Formatter: Ruff (`ruff format .`)
- Linter: Ruff (`ruff check .`)
- Type checker: mypy strict on `packages/core/`
- Test runner: pytest with `asyncio_mode = "auto"`
- `S101` (assert) is allowed in test files

```bash
make lint          # ruff check + eslint
make type-check    # mypy + svelte-check
make format        # ruff format + prettier
```

### TypeScript / Svelte

- 2-space indent
- `no-explicit-any` is an error
- Unused args prefixed with `_` (e.g., `_event`)
- Path aliases: `$lib`, `$components`

### Testing requirements

- **Minimum coverage: 40%** — enforced locally by `make test-cov` (target is 80%, threshold being raised incrementally)
- All new routes must have integration tests
- All Semgrep rules must have test files in the same directory
- No mocking the database in integration tests — use a real DB

```bash
make test          # run all tests
make test-cov      # with coverage report (fails under 40%)
make test-rules    # semgrep --test on all rules
```

## Adding a Semgrep rule

Every rule must link to a real documented incident.

1. Create the rule file: `packages/semgrep-rules/rules/{category}/{category}-{NNN}.yaml`

```yaml
rules:
  - id: unsafe-regex-002
    message: |
      Unbounded quantifier on user input can cause catastrophic backtracking.
      Use atomic groups or possessive quantifiers, or limit input length before matching.
      Incident: [2026-01-15 Regex DoS] — regex took 45s on a 10KB string, caused timeout.
    severity: ERROR
    languages: [python]
    pattern: re.compile($PATTERN)
    metadata:
      category: unsafe-regex
      incident_url: https://your-postmortem-url
      created: 2026-03-28
```

2. Create the test file: `packages/semgrep-rules/rules/{category}/{category}-{NNN}.test.py`

```python
# ruleid: unsafe-regex-002
re.compile(user_input)

# ok: safe usage
re.compile(r"^[a-z]{1,100}$")
```

3. Run the tests: `make test-rules`

4. Register the rule in `packages/semgrep-rules/metadata/registry.json`.

## Adding a database migration

```bash
# Auto-generate from model changes
make migrate-gen MSG="add_column_foo_to_bar"

# Or write manually in packages/db/src/migrations/versions/
```

Migration files are tracked in git normally (not ignored). Just `git add` as usual.

Always include both `upgrade()` and `downgrade()` implementations.

## Architecture rules (Constitution)

These are non-negotiable — the CI/CD pipeline enforces most of them:

1. **Incident traceability** — every Semgrep rule links to a real incident
2. **Hexagonal boundaries** — `packages/core/` must not import from `apps/` or `packages/db/`
3. **Port/adapter discipline** — new external dependencies require a port interface first
4. **Incremental complexity** — L1 must work before L2, L2 before L3. New abstractions require 2 concrete implementations
5. **TDD** — tests before implementation, coverage threshold at 40% (target 80%)
6. **No service account keys** — all GCP auth via Workload Identity Federation
7. **RLS everywhere** — all tenant-scoped tables must have RLS policies

Full constitution at `.specify/memory/constitution.md`.

## Pre-commit hooks

Configured automatically by `dev-setup.sh`:

- Ruff (lint + format)
- mypy strict on `packages/core/`
- Semgrep scan on staged Python files
- Trailing whitespace, EOF newlines, YAML/JSON validity
- No large files (> 500KB)

Run manually: `pre-commit run --all-files`

## PR checklist

Before opening a PR, verify:

- [ ] Tests pass locally (`make test`)
- [ ] Coverage >= 40% (`make test-cov`)
- [ ] Types check clean (`make type-check`)
- [ ] Linting passes (`make lint`)
- [ ] If adding a Semgrep rule: test file exists and `make test-rules` passes
- [ ] If adding a migration: both `upgrade()` and `downgrade()` implemented
- [ ] Commit messages follow Conventional Commits
- [ ] PR description explains the *why*, not just the *what*

## Language

Code and public-facing docs: **English**. Internal docs and PR descriptions: **PT-BR** is fine.
