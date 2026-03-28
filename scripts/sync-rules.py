#!/usr/bin/env python3
"""
T185: sync-rules.py — Sync Semgrep rules to GitHub App / API consumers.

Reads all YAML rule files from packages/semgrep-rules/ and either:
  --target github   Push rules to the GitHub App (as a .semgrep/ folder commit)
  --target api      POST/PUT rules to the Oute Muscle REST API
  --target stdout   Print a merged YAML to stdout (default, no credentials needed)

Usage:
  python scripts/sync-rules.py --target stdout
  python scripts/sync-rules.py --target api --api-url https://api.oute.me --api-key $API_KEY
  python scripts/sync-rules.py --target github --repo owner/repo --token $GITHUB_TOKEN

Exit codes:
  0 — success
  1 — validation error (broken YAML, missing required fields)
  2 — network / API error
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml  # PyYAML

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
RULES_DIR = REPO_ROOT / "packages" / "semgrep-rules"

REQUIRED_RULE_FIELDS = {"id", "message", "severity", "languages", "pattern"}


# ---------------------------------------------------------------------------
# Rule loading and validation
# ---------------------------------------------------------------------------


def load_rules(rules_dir: Path) -> list[dict]:
    """
    Recursively load all *.yml / *.yaml files under rules_dir.
    Returns a flat list of individual rule dicts (each file may define >1 rule).
    """
    rules: list[dict] = []
    errors: list[str] = []

    for path in sorted(rules_dir.rglob("*.yml")) + sorted(rules_dir.rglob("*.yaml")):
        if "test" in path.parts or path.stem.endswith("-test"):
            continue  # skip test files
        try:
            with path.open() as f:
                doc = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            errors.append(f"{path}: YAML parse error — {exc}")
            continue

        if not isinstance(doc, dict) or "rules" not in doc:
            errors.append(f"{path}: missing top-level 'rules' key")
            continue

        for rule in doc["rules"]:
            missing = REQUIRED_RULE_FIELDS - set(rule.keys())
            if "patterns" in rule or "pattern-either" in rule or "pattern" in rule:
                missing.discard("pattern")  # accept compound patterns
            if missing:
                errors.append(f"{path} rule '{rule.get('id', '?')}': missing fields {missing}")
                continue
            rules.append(rule)

    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(1)

    return rules


# ---------------------------------------------------------------------------
# Targets
# ---------------------------------------------------------------------------


def target_stdout(rules: list[dict]) -> None:
    """Print merged YAML to stdout."""
    merged = {"rules": rules}
    print(yaml.dump(merged, default_flow_style=False, allow_unicode=True))


def target_api(rules: list[dict], api_url: str, api_key: str) -> None:
    """
    Sync rules to the Oute Muscle REST API.
    Uses PATCH /rules/{id} (update) or POST /rules (create) per rule.
    """
    try:
        import httpx
    except ImportError:
        print(
            "ERROR: httpx is required for --target api. Install with: pip install httpx",
            file=sys.stderr,
        )
        sys.exit(2)

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    created = updated = failed = 0

    with httpx.Client(base_url=api_url, headers=headers, timeout=30) as client:
        # Fetch existing rules for diff
        resp = client.get("/rules", params={"page_size": 1000})
        if resp.status_code != 200:
            print(f"ERROR: GET /rules failed: {resp.status_code} {resp.text}", file=sys.stderr)
            sys.exit(2)
        existing = {r["rule_id"]: r for r in resp.json().get("items", [])}

        for rule in rules:
            rule_id = rule["id"]
            payload = {
                "rule_id": rule_id,
                "title": rule.get("message", rule_id),
                "category": _infer_category(rule_id),
                "severity": rule.get("severity", "WARNING").lower(),
                "rule_yaml": yaml.dump({"rules": [rule]}, default_flow_style=False),
                "languages": rule.get("languages", []),
            }

            if rule_id in existing:
                resp = client.patch(f"/rules/{rule_id}", json=payload)
                action = "updated"
            else:
                resp = client.post("/rules", json=payload)
                action = "created"

            if resp.status_code in (200, 201):
                print(f"  ✓ {action}: {rule_id}")
                if action == "created":
                    created += 1
                else:
                    updated += 1
            else:
                print(
                    f"  ✗ {action} failed for {rule_id}: {resp.status_code} {resp.text}",
                    file=sys.stderr,
                )
                failed += 1

    print(f"\nSync complete: {created} created, {updated} updated, {failed} failed")
    if failed:
        sys.exit(2)


def target_github(rules: list[dict], repo: str, token: str, branch: str = "main") -> None:
    """
    Push a merged .semgrep/rules.yml to the specified GitHub repository.
    Creates or updates the file on the given branch.
    """
    try:
        import httpx
    except ImportError:
        print(
            "ERROR: httpx is required for --target github. Install with: pip install httpx",
            file=sys.stderr,
        )
        sys.exit(2)

    import base64

    merged_yaml = yaml.dump({"rules": rules}, default_flow_style=False, allow_unicode=True)
    encoded = base64.b64encode(merged_yaml.encode()).decode()

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    file_path = ".semgrep/rules.yml"
    api_url = f"https://api.github.com/repos/{repo}/contents/{file_path}"

    with httpx.Client(headers=headers, timeout=30) as client:
        # Check if file already exists to get its SHA
        get_resp = client.get(api_url, params={"ref": branch})
        sha: str | None = None
        if get_resp.status_code == 200:
            sha = get_resp.json()["sha"]

        payload = {
            "message": f"chore: sync Semgrep rules ({len(rules)} rules)",
            "content": encoded,
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha

        put_resp = client.put(api_url, json=payload)
        if put_resp.status_code in (200, 201):
            action = "Updated" if sha else "Created"
            print(f"✓ {action} {file_path} on {repo}@{branch} ({len(rules)} rules)")
        else:
            print(f"✗ GitHub API error: {put_resp.status_code} {put_resp.text}", file=sys.stderr)
            sys.exit(2)


def _infer_category(rule_id: str) -> str:
    """Extract category from rule ID (e.g. 'unsafe-regex-001' → 'unsafe-regex')."""
    parts = rule_id.rsplit("-", 1)
    return parts[0] if len(parts) == 2 and parts[1].isdigit() else rule_id


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync Oute Muscle Semgrep rules to consumers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--target",
        choices=["stdout", "api", "github"],
        default="stdout",
        help="Sync target (default: stdout)",
    )
    parser.add_argument("--rules-dir", type=Path, default=RULES_DIR)

    # API target
    parser.add_argument("--api-url", default="https://api.oute.me")
    parser.add_argument("--api-key", default="")

    # GitHub target
    parser.add_argument("--repo", default="", help="owner/repo")
    parser.add_argument("--token", default="", help="GitHub personal access token")
    parser.add_argument("--branch", default="main")

    args = parser.parse_args()

    rules = load_rules(args.rules_dir)
    print(f"Loaded {len(rules)} rules from {args.rules_dir}", file=sys.stderr)

    if args.target == "stdout":
        target_stdout(rules)
    elif args.target == "api":
        if not args.api_key:
            print("ERROR: --api-key is required for --target api", file=sys.stderr)
            sys.exit(1)
        target_api(rules, api_url=args.api_url, api_key=args.api_key)
    elif args.target == "github":
        if not args.repo or not args.token:
            print("ERROR: --repo and --token are required for --target github", file=sys.stderr)
            sys.exit(1)
        target_github(rules, repo=args.repo, token=args.token, branch=args.branch)


if __name__ == "__main__":
    main()
