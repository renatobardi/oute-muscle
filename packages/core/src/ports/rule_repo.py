"""RuleRepo port — abstracts Semgrep rule persistence."""

from __future__ import annotations

import uuid
from typing import Protocol, runtime_checkable

from ..domain.incidents.enums import IncidentCategory
from ..domain.rules.entity import SemgrepRule


@runtime_checkable
class RuleRepoPort(Protocol):
    """Port for SemgrepRule persistence. Implemented by PostgreSQL adapter."""

    async def create(self, rule: SemgrepRule) -> SemgrepRule:
        """Persist a new rule.

        Raises:
            DuplicateRuleIdError: If rule ID already exists.
            RuleRepoError: For other failures.
        """
        ...

    async def get_by_id(self, rule_id: str) -> SemgrepRule | None:
        """Retrieve a rule by its category-prefixed ID (e.g. 'unsafe-regex-001')."""
        ...

    async def list_active(
        self,
        *,
        tenant_id: uuid.UUID | None = None,
        category: IncidentCategory | None = None,
    ) -> list[SemgrepRule]:
        """List all enabled (non-auto-disabled) rules."""
        ...

    async def toggle(self, rule_id: str, *, enabled: bool, tenant_id: uuid.UUID) -> SemgrepRule:
        """Enable or disable a rule.

        Raises:
            RuleNotFoundError: If rule_id does not exist.
        """
        ...

    async def next_sequence_number(
        self, category: IncidentCategory, *, tenant_id: uuid.UUID | None = None
    ) -> int:
        """Return the next available sequence number for a category.

        Used to generate the rule ID suffix (e.g. category has 3 rules → returns 4).
        """
        ...

    async def increment_false_positive(self, rule_id: str, *, tenant_id: uuid.UUID) -> SemgrepRule:
        """Increment false_positive_count; auto-disable at threshold 3."""
        ...


class RuleRepoError(Exception):
    """Base error for rule repository failures."""


class DuplicateRuleIdError(RuleRepoError):
    """Raised when a rule with the same ID already exists."""


class RuleNotFoundError(RuleRepoError):
    """Raised when a rule is not found."""
