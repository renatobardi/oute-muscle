"""PostgreSQL rule repository adapter (RuleRepoPort implementation).

Constitution VI: Adapter implements port with real PostgreSQL persistence.
"""

from __future__ import annotations

import uuid

from ..domain.incidents.enums import IncidentCategory
from ..domain.rules.entity import SemgrepRule
from ..ports.rule_repo import RuleRepoPort


class PostgreSQLRuleRepo(RuleRepoPort):
    """PostgreSQL adapter for RuleRepoPort."""

    async def create(self, rule: SemgrepRule) -> SemgrepRule:
        """Persist a new rule."""
        raise NotImplementedError("PostgreSQL adapter implementation pending")

    async def get_by_id(self, rule_id: str) -> SemgrepRule | None:
        """Retrieve a rule by ID."""
        raise NotImplementedError("PostgreSQL adapter implementation pending")

    async def list_active(
        self,
        *,
        tenant_id: uuid.UUID | None = None,
        category: IncidentCategory | None = None,
    ) -> list[SemgrepRule]:
        """List active rules with optional filtering."""
        raise NotImplementedError("PostgreSQL adapter implementation pending")

    async def toggle_active(self, rule_id: str, is_active: bool) -> None:
        """Enable or disable a rule."""
        raise NotImplementedError("PostgreSQL adapter implementation pending")

    async def next_sequence_number(self, category: IncidentCategory) -> int:
        """Get the next sequence number for a category."""
        raise NotImplementedError("PostgreSQL adapter implementation pending")
