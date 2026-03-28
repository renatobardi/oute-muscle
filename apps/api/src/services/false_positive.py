"""
False positive reporting service.

Business rules:
  - Any editor or admin can report a finding as a false positive
  - Each report increments false_positive_count on the finding
  - The first report sets status = 'false_positive'
  - When count reaches FALSE_POSITIVE_DISABLE_THRESHOLD (3), the source rule
    is automatically disabled (enabled=False) to prevent future noisy matches
  - If the rule is already disabled, no second disable is issued
"""

from __future__ import annotations

from typing import Any, Optional, Protocol

FALSE_POSITIVE_DISABLE_THRESHOLD: int = 3


class FindingNotFound(Exception):
    def __init__(self, finding_id: str):
        super().__init__(f"Finding '{finding_id}' not found")
        self.finding_id = finding_id


class FindingRepo(Protocol):
    async def get(self, finding_id: str) -> Optional[Any]: ...
    async def save(self, finding: Any) -> Any: ...


class RuleRepo(Protocol):
    async def get(self, rule_id: str) -> Optional[Any]: ...
    async def disable(self, rule_id: str) -> None: ...


class FalsePositiveService:
    """
    Handles the false-positive reporting lifecycle for a finding.
    All dependencies are injected for testability.
    """

    def __init__(
        self,
        finding_repo: FindingRepo,
        rule_repo: RuleRepo,
    ) -> None:
        self._finding_repo = finding_repo
        self._rule_repo = rule_repo

    async def report(self, finding_id: str, reported_by: str) -> Any:
        """
        Mark a finding as a false positive and conditionally disable its rule.

        Returns the updated finding object.
        Raises FindingNotFound if the finding does not exist.
        """
        finding = await self._finding_repo.get(finding_id)
        if finding is None:
            raise FindingNotFound(finding_id)

        # Update the finding
        finding.status = "false_positive"
        finding.false_positive_count = getattr(finding, "false_positive_count", 0) + 1

        await self._finding_repo.save(finding)

        # Auto-disable rule at threshold
        if finding.false_positive_count >= FALSE_POSITIVE_DISABLE_THRESHOLD:
            rule_id = getattr(finding, "rule_id", None)
            if rule_id:
                rule = await self._rule_repo.get(rule_id)
                if rule is not None and getattr(rule, "enabled", False):
                    await self._rule_repo.disable(rule_id)

        return finding
