"""synthesize_rules MCP tool — Enterprise only.

Input: { incident_ids: list[str], tenant_id: str, tier: str }
Output: { candidate_id: str, status: "queued" }

Guard: if tier != "enterprise" → raise EnterpriseTierRequired
"""

from __future__ import annotations

import uuid
from typing import Any

from apps.mcp.src.metering import MeteringService


class EnterpriseTierRequiredError(Exception):
    """This feature requires Enterprise tier."""

    pass


async def synthesize_rules(
    incident_ids: list[str],
    tenant_id: str,
    user_id: str,
    tier: str,
    metering: MeteringService | None = None,
) -> dict[str, Any]:
    """Synthesize new detection rules from incidents.

    Args:
        incident_ids: Incidents to synthesize from
        tenant_id: Tenant identifier
        user_id: User identifier
        tier: User tier (enterprise required)
        metering: Metering service

    Returns:
        Dict with candidate_id and status

    Raises:
        EnterpriseTierRequired: If user is not enterprise tier
    """
    if tier != "enterprise":
        raise EnterpriseTierRequiredError(f"Synthesis requires Enterprise tier, got {tier}")

    if metering is None:
        metering = MeteringService()

    # Increment metering
    metering.increment(user_id, tier)

    # Create synthesis candidate (stub for now)
    candidate_id = str(uuid.uuid4())

    if synthesis_repo and hasattr(synthesis_repo, "create_candidate"):
        result = await synthesis_repo.create_candidate(  # type: ignore
            incident_ids=incident_ids,
            tenant_id=tenant_id,
            user_id=user_id,
        )
    else:
        result = {
            "candidate_id": candidate_id,
            "status": "queued",
        }

    return {
        "candidate_id": result.get("candidate_id", candidate_id),
        "status": result.get("status", "queued"),
    }


# Stub for synthesis repo
synthesis_repo = None
