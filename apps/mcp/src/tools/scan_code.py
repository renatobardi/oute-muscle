"""scan_code MCP tool — real Semgrep execution.

Input: { code: str, language: str, tenant_id: str }
Output: { findings: list[dict], scan_id: str, scanned_at: str }

Each finding dict:
    { rule_id, message, severity, line, end_line, path, incident_id | null }

Semgrep is invoked as a subprocess with the project's rule set
(packages/semgrep-rules/).  If Semgrep is not installed or the rules
path does not exist the tool falls back gracefully to an empty result.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
import uuid
from datetime import UTC, datetime
from typing import Any

from apps.mcp.src.metering import MeteringService, QuotaExceededError

logger = logging.getLogger(__name__)

# Map language names to file extensions for temp file creation
_LANGUAGE_EXTENSIONS: dict[str, str] = {
    "python": ".py",
    "py": ".py",
    "javascript": ".js",
    "js": ".js",
    "typescript": ".ts",
    "ts": ".ts",
    "java": ".java",
    "go": ".go",
    "ruby": ".rb",
    "rb": ".rb",
    "rust": ".rs",
    "c": ".c",
    "cpp": ".cpp",
    "c++": ".cpp",
    "kotlin": ".kt",
    "swift": ".swift",
    "php": ".php",
    "scala": ".scala",
    "bash": ".sh",
    "sh": ".sh",
}


async def scan_code(
    code: str,
    language: str,
    tenant_id: str,
    user_id: str,
    tier: str = "free",
    metering: MeteringService | None = None,
) -> dict[str, Any]:
    """Scan code for incidents using Semgrep.

    Writes code to a temporary file, invokes the Semgrep CLI with the
    project's bundled rules, and returns structured findings.

    Args:
        code: Source code to scan.
        language: Programming language (e.g. 'python', 'javascript').
        tenant_id: Tenant identifier (for future per-tenant rule filtering).
        user_id: User identifier for quota tracking.
        tier: Subscription tier — controls quota limits.
        metering: MeteringService instance (created fresh if None).

    Returns:
        Dict with keys:
            findings  – list of finding dicts
            scan_id   – unique UUID for this scan
            scanned_at – ISO-8601 timestamp

    Raises:
        QuotaExceededError: If the user has exceeded their scan quota.
    """
    if metering is None:
        metering = MeteringService()

    if not metering.quota_ok(user_id, tier):
        limit = 50 if tier == "free" else (500 if tier == "team" else None)
        current = metering.get_count(user_id)
        raise QuotaExceededError(user_id, limit, current)

    metering.increment(user_id, tier)

    findings = await run_semgrep(code, language)

    return {
        "findings": findings,
        "scan_id": str(uuid.uuid4()),
        "scanned_at": datetime.now(UTC).isoformat(),
    }


async def run_semgrep(code: str, language: str) -> list[dict[str, Any]]:
    """Run Semgrep on code and return structured findings.

    Creates a temporary file with the appropriate extension, runs
    ``semgrep --config <rules_path> --json --quiet <file>``, and parses
    the JSON output into normalised finding dicts.

    Falls back to an empty list when:
    - Semgrep is not installed
    - The rules path does not exist
    - Semgrep times out (30 s)
    - The output cannot be parsed

    Args:
        code: Source code to scan.
        language: Programming language string.

    Returns:
        List of finding dicts, each containing:
            rule_id, message, severity, line, end_line, path, incident_id
    """
    if not code.strip():
        return []

    rules_path = os.environ.get("SEMGREP_RULES_PATH", "packages/semgrep-rules")
    if not os.path.exists(rules_path):
        logger.warning("semgrep_rules_not_found", path=rules_path)
        return []

    ext = _LANGUAGE_EXTENSIONS.get(language.lower(), ".txt")

    with tempfile.NamedTemporaryFile(suffix=ext, mode="w", delete=False) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        proc = await asyncio.create_subprocess_exec(
            "semgrep",
            "--config", rules_path,
            "--json",
            "--quiet",
            "--no-git-ignore",
            tmp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
        except asyncio.TimeoutError:
            proc.kill()
            logger.warning("semgrep_timeout", language=language)
            return []
    except FileNotFoundError:
        logger.warning("semgrep_not_installed")
        return []
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    if stderr:
        logger.debug("semgrep_stderr", stderr=stderr.decode(errors="replace")[:500])

    try:
        output = json.loads(stdout.decode())
    except json.JSONDecodeError as exc:
        logger.warning("semgrep_json_parse_error", error=str(exc))
        return []

    return [_normalise_finding(r) for r in output.get("results", [])]


def _normalise_finding(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalise a raw Semgrep result dict to the MCP tool output format.

    Rule IDs in the Oute Muscle format: ``{category}-{NNN}``.
    The incident_id is extracted from the rule metadata if present.

    Args:
        raw: Raw finding dict from Semgrep JSON output.

    Returns:
        Normalised finding dict.
    """
    extra: dict = raw.get("extra", {})
    metadata: dict = extra.get("metadata", {})

    return {
        "rule_id": raw.get("check_id", "unknown"),
        "message": extra.get("message", ""),
        "severity": extra.get("severity", "low").lower(),
        "line": raw.get("start", {}).get("line", 1),
        "end_line": raw.get("end", {}).get("line", 1),
        "path": raw.get("path", ""),
        "incident_id": metadata.get("incident_id"),  # None if not set in rule YAML
    }
