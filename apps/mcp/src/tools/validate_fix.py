"""validate_fix MCP tool.

Input: { original_code: str, fixed_code: str, rule_id: str, tenant_id: str }
Output: { status: "pass" | "fail", remaining_findings: list[dict] }

Re-runs scan_code on fixed_code with same rule_id.
If no findings → pass. Else → fail with remaining findings.
"""

from __future__ import annotations

from typing import Any

from apps.mcp.src.metering import MeteringService, QuotaExceededError
from apps.mcp.src.tools.scan_code import scan_code


async def validate_fix(
    original_code: str,
    fixed_code: str,
    rule_id: str,
    tenant_id: str,
    user_id: str,
    tier: str = "free",
    metering: MeteringService | None = None,
) -> dict[str, Any]:
    """Validate that a fix resolves the issue.

    Args:
        original_code: Original code with issue
        fixed_code: Proposed fixed code
        rule_id: Rule to check
        tenant_id: Tenant identifier
        user_id: User identifier
        tier: User tier
        metering: Metering service

    Returns:
        Dict with status and remaining_findings

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

    # Re-scan the fixed code
    result = await scan_code(
        code=fixed_code,
        language="python",  # Assume Python for now
        tenant_id=tenant_id,
        user_id=user_id,
        tier=tier,
        metering=metering,
    )

    findings = result.get("findings", [])

    if not findings:
        return {"status": "pass"}
    else:
        return {
            "status": "fail",
            "remaining_findings": findings,
        }
