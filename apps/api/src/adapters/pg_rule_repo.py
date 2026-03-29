"""PostgreSQL adapter for SemgrepRule persistence.

Used by the synthesis approval flow (SynthesisService.approve) to promote
a synthesis candidate into a Layer 1 Semgrep rule.

This adapter sits in apps/api (not packages/core) because it depends on
SQLAlchemy models from packages/db — which packages/core must not import.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from packages.db.src.models.rule import SemgrepRule as SemgrepRuleModel

logger = logging.getLogger(__name__)


class PostgreSQLRuleRepo:
    """PostgreSQL-backed rule repository.

    Uses SessionFactory rather than a per-request session because the synthesis
    route injects this via app.state.
    """

    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory

    async def create(self, rule_data: dict[str, Any]) -> SemgrepRuleModel:
        """Insert a new SemgrepRule row from synthesis approval.

        Accepts a loose dict from SynthesisService.approve() containing keys:
            id              - rule ID string (e.g. 'unsafe-regex-042')
            yaml            - full YAML content
            approved_by     - user ID who approved
            source          - 'synthesized' | 'manual'
            incident_id     - UUID or None

        Returns the persisted SemgrepRuleModel.
        """
        rule_id: str = rule_data.get("id") or f"synthesized-{uuid.uuid4().hex[:8]}"
        yaml_content: str = rule_data.get("yaml") or rule_data.get("yaml_content", "")
        approved_by_raw = rule_data.get("approved_by")
        source: str = rule_data.get("source", "synthesized")
        incident_id_raw = rule_data.get("incident_id")

        # Resolve UUIDs safely
        try:
            approved_by_uuid: uuid.UUID | None = (
                uuid.UUID(str(approved_by_raw)) if approved_by_raw else None
            )
        except ValueError:
            approved_by_uuid = None

        try:
            incident_id_uuid: uuid.UUID | None = (
                uuid.UUID(str(incident_id_raw)) if incident_id_raw else None
            )
        except ValueError:
            incident_id_uuid = None

        # Derive category from rule_id prefix (e.g. "unsafe-regex-042" → "unsafe-regex")
        parts = rule_id.rsplit("-", 1)
        category = parts[0] if len(parts) == 2 else "synthesized"

        async for session in self._session_factory.get_session():
            try:
                # Check for duplicate — treat as idempotent (return existing row)
                from sqlalchemy import select

                existing = await session.execute(
                    select(SemgrepRuleModel).where(SemgrepRuleModel.id == rule_id)
                )
                row = existing.scalar_one_or_none()
                if row is not None:
                    logger.info(
                        "rule_repo.create: rule %s already exists, returning existing", rule_id
                    )
                    return row

                row = SemgrepRuleModel(
                    id=rule_id,
                    tenant_id=None,  # public rule (synthesized rules start public)
                    incident_id=incident_id_uuid,
                    category=category,
                    sequence_number=1,
                    yaml_content=yaml_content,
                    test_file_content="",  # synthesis doesn't generate tests yet
                    severity="warning",
                    message=rule_data.get("message", ""),
                    remediation=rule_data.get("remediation", ""),
                    source=source,
                    is_approved=approved_by_uuid is not None,
                    approved_by=approved_by_uuid,
                    is_active=True,
                )
                session.add(row)
                await session.commit()
                await session.refresh(row)
                logger.info("rule_repo.create: persisted rule %s", rule_id)
                return row
            except Exception as exc:
                await session.rollback()
                logger.error("rule_repo.create failed for %s: %s", rule_id, exc)
                raise

        raise RuntimeError("No session available in rule_repo.create")

    async def get_by_id(self, rule_id: str) -> SemgrepRuleModel | None:
        """Fetch a rule by its string ID.

        Args:
            rule_id: The rule string ID (e.g. 'unsafe-regex-001').

        Returns:
            SemgrepRuleModel or None if not found.
        """
        from sqlalchemy import select

        async for session in self._session_factory.get_session():
            try:
                result = await session.execute(
                    select(SemgrepRuleModel).where(SemgrepRuleModel.id == rule_id)
                )
                return result.scalar_one_or_none()
            except Exception as exc:
                logger.warning("rule_repo.get_by_id %s failed: %s", rule_id, exc)
                return None

        return None

    async def toggle_active(self, rule_id: str, *, is_active: bool) -> None:
        """Enable or disable a rule.

        Args:
            rule_id: The rule string ID.
            is_active: True to enable, False to disable.
        """
        from sqlalchemy import update

        async for session in self._session_factory.get_session():
            try:
                await session.execute(
                    update(SemgrepRuleModel)
                    .where(SemgrepRuleModel.id == rule_id)
                    .values(is_active=is_active)
                )
                await session.commit()
            except Exception as exc:
                await session.rollback()
                logger.error("rule_repo.toggle_active %s failed: %s", rule_id, exc)
            return

    async def list_active(
        self,
        *,
        tenant_id: uuid.UUID | None = None,
        category: str | None = None,
        limit: int = 200,
    ) -> list[SemgrepRuleModel]:
        """List active (non-disabled) rules.

        Args:
            tenant_id: Optional tenant filter; None returns public rules.
            category: Optional category filter (e.g. 'unsafe-regex').
            limit: Max rows to return.

        Returns:
            List of SemgrepRuleModel.
        """
        from sqlalchemy import select

        async for session in self._session_factory.get_session():
            try:
                stmt = select(SemgrepRuleModel).where(SemgrepRuleModel.is_active.is_(True))
                if tenant_id is not None:
                    stmt = stmt.where(SemgrepRuleModel.tenant_id == tenant_id)
                if category is not None:
                    stmt = stmt.where(SemgrepRuleModel.category == category)
                stmt = stmt.limit(limit)
                result = await session.execute(stmt)
                return list(result.scalars().all())
            except Exception as exc:
                logger.warning("rule_repo.list_active failed: %s", exc)
                return []

        return []

    async def next_sequence_number(
        self,
        category: str,
        *,
        tenant_id: uuid.UUID | None = None,
    ) -> int:
        """Return the next available sequence number for the given category.

        Args:
            category: Rule category (e.g. 'unsafe-regex').
            tenant_id: Optional tenant scope.

        Returns:
            Next integer sequence (max existing + 1, or 1 if none).
        """
        from sqlalchemy import func, select

        async for session in self._session_factory.get_session():
            try:
                stmt = select(func.max(SemgrepRuleModel.sequence_number)).where(
                    SemgrepRuleModel.category == category
                )
                if tenant_id is not None:
                    stmt = stmt.where(SemgrepRuleModel.tenant_id == tenant_id)
                result = await session.execute(stmt)
                current_max = result.scalar_one_or_none()
                return (current_max or 0) + 1
            except Exception as exc:
                logger.warning("rule_repo.next_sequence_number failed: %s", exc)
                return 1

        return 1
