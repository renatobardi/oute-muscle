"""scan_code MCP tool.

Input: { code: str, language: str, tenant_id: str }
Output: { findings: list[dict], scan_id: str, scanned_at: str }

Each finding dict: { rule_id, message, severity, line, incident_id | null }
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from apps.mcp.src.metering import MeteringService, QuotaExceededError


async def scan_code(
    code: str,
    language: str,
    tenant_id: str,
    user_id: str,
    tier: str = "free",
    metering: MeteringService | None = None,
) -> dict:
    """Scan code for issues using Semgrep.

    Args:
        code: Code to scan
        language: Programming language
        tenant_id: Tenant identifier
        user_id: User identifier
        tier: User tier (free, team, enterprise)
        metering: Metering service

    Returns:
        Dict with findings list, scan_id, and scanned_at timestamp

    Raises:
        QuotaExceededError: If user quota exceeded
    """
    if metering is None:
        metering = MeteringService()

    # Check quota before executing
    if not metering.quota_ok(user_id, tier):
        limit = 50 if tier == "free" else (500 if tier == "team" else None)
        current = metering.get_count(user_id)
        raise QuotaExceededError(user_id, limit, current)

    # Increment metering
    metering.increment(user_id, tier)

    # Stub Semgrep execution (return empty findings for now)
    findings = run_semgrep(code, language)

    scan_id = str(uuid.uuid4())
    scanned_at = datetime.now(timezone.utc).isoformat()

    return {
        "findings": findings,
        "scan_id": scan_id,
        "scanned_at": scanned_at,
    }


def run_semgrep(code: str, language: str) -> list[dict]:
    """Stub Semgrep execution.

    Args:
        code: Code to scan
        language: Programming language

    Returns:
        List of finding dicts
    """
    # Stub implementation - return empty findings
    # Real implementation would call Semgrep CLI or API
    return []
