"""PostgreSQL incident repository — real implementation of IncidentRepoPort.

Constitution VI: Adapter implements port with real PostgreSQL persistence.
Uses optimistic locking (version column), soft delete (deleted_at), and RLS.

Placed in packages/db because it needs SQLAlchemy + pgvector deps.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import and_, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.src.domain.incidents.entity import Incident as IncidentEntity
from packages.core.src.domain.incidents.enums import IncidentCategory, IncidentSeverity
from packages.core.src.ports.incident_repo import (
    DuplicateSourceUrlError,
    IncidentHasActiveRuleError,
    IncidentRepoError,
    OptimisticLockError,
)

from ..models.incident import Incident as IncidentModel


def _model_to_entity(model: IncidentModel) -> IncidentEntity:
    """Convert SQLAlchemy Incident model to domain entity."""
    return IncidentEntity(
        id=model.id,
        tenant_id=model.tenant_id,
        title=model.title,
        date=model.date,
        source_url=model.source_url,
        organization=model.organization,
        category=IncidentCategory(model.category),
        subcategory=model.subcategory,
        failure_mode=model.failure_mode,
        severity=IncidentSeverity(model.severity),
        affected_languages=list(model.affected_languages) if model.affected_languages else [],
        anti_pattern=model.anti_pattern,
        code_example=model.code_example,
        remediation=model.remediation,
        tags=list(model.tags) if model.tags else [],
        static_rule_possible=bool(model.static_rule_possible),
        semgrep_rule_id=model.semgrep_rule_id,
        embedding=list(model.embedding) if model.embedding is not None else None,
        version=model.version,
        deleted_at=model.deleted_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
        created_by=model.created_by or uuid.UUID(int=0),  # fallback for seeded incidents
    )


class PostgreSQLIncidentRepo:
    """PostgreSQL adapter for IncidentRepoPort.

    Receives an AsyncSession per request (injected via FastAPI Depends).
    RLS is enforced at the DB level via SET LOCAL app.tenant_id in TenantContextSession.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, incident: IncidentEntity) -> IncidentEntity:
        """Persist a new incident. Raises DuplicateSourceUrlError on duplicate URL."""
        if incident.source_url:
            existing = await self._session.execute(
                select(IncidentModel).where(IncidentModel.source_url == incident.source_url)
            )
            if existing.scalar_one_or_none() is not None:
                raise DuplicateSourceUrlError(
                    f"source_url already exists: {incident.source_url}"
                )

        model = IncidentModel(
            id=incident.id,
            tenant_id=incident.tenant_id,
            title=incident.title,
            date=incident.date,
            source_url=incident.source_url,
            organization=incident.organization,
            category=str(incident.category.value),
            subcategory=incident.subcategory,
            failure_mode=incident.failure_mode,
            severity=str(incident.severity.value),
            affected_languages=incident.affected_languages,
            anti_pattern=incident.anti_pattern,
            code_example=incident.code_example,
            remediation=incident.remediation,
            tags=incident.tags,
            static_rule_possible=incident.static_rule_possible,
            semgrep_rule_id=incident.semgrep_rule_id,
            embedding=incident.embedding,
            version=1,
            created_by=incident.created_by,
        )
        self._session.add(model)
        try:
            await self._session.commit()
        except IntegrityError as e:
            await self._session.rollback()
            if "source_url" in str(e):
                raise DuplicateSourceUrlError(str(e)) from e
            raise IncidentRepoError(str(e)) from e
        await self._session.refresh(model)
        return _model_to_entity(model)

    async def get_by_id(
        self, incident_id: uuid.UUID, *, tenant_id: uuid.UUID | None = None
    ) -> IncidentEntity | None:
        """Retrieve incident by ID. Returns None if not found or soft-deleted."""
        stmt = select(IncidentModel).where(
            IncidentModel.id == incident_id,
            IncidentModel.deleted_at.is_(None),
        )
        if tenant_id is not None:
            stmt = stmt.where(
                or_(
                    IncidentModel.tenant_id == tenant_id,
                    IncidentModel.tenant_id.is_(None),
                )
            )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _model_to_entity(model) if model else None

    async def update(self, incident: IncidentEntity, *, expected_version: int) -> IncidentEntity:
        """Update incident with optimistic locking. Raises OptimisticLockError on version mismatch."""
        stmt = (
            update(IncidentModel)
            .where(
                and_(
                    IncidentModel.id == incident.id,
                    IncidentModel.version == expected_version,
                    IncidentModel.deleted_at.is_(None),
                )
            )
            .values(
                title=incident.title,
                date=incident.date,
                organization=incident.organization,
                category=str(incident.category.value),
                subcategory=incident.subcategory,
                failure_mode=incident.failure_mode,
                severity=str(incident.severity.value),
                affected_languages=incident.affected_languages,
                anti_pattern=incident.anti_pattern,
                code_example=incident.code_example,
                remediation=incident.remediation,
                tags=incident.tags,
                static_rule_possible=incident.static_rule_possible,
                semgrep_rule_id=incident.semgrep_rule_id,
                embedding=incident.embedding,
                version=expected_version + 1,
                updated_at=dt.datetime.utcnow(),
            )
            .returning(IncidentModel)
        )
        result = await self._session.execute(stmt)
        updated = result.scalar_one_or_none()
        if updated is None:
            raise OptimisticLockError(
                f"Version conflict on incident {incident.id}: "
                f"expected version {expected_version} but was modified concurrently."
            )
        await self._session.commit()
        return _model_to_entity(updated)

    async def soft_delete(self, incident_id: uuid.UUID, *, tenant_id: uuid.UUID) -> None:
        """Set deleted_at. Raises IncidentHasActiveRuleError if semgrep_rule_id is set."""
        result = await self._session.execute(
            select(IncidentModel).where(
                IncidentModel.id == incident_id,
                IncidentModel.deleted_at.is_(None),
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return  # Already deleted or not found — idempotent

        if model.semgrep_rule_id is not None:
            raise IncidentHasActiveRuleError(
                f"Cannot delete incident {incident_id}: "
                f"it has active Semgrep rule '{model.semgrep_rule_id}'. "
                "Disable or unlink the rule first."
            )

        model.deleted_at = dt.datetime.utcnow()
        await self._session.commit()

    async def hard_delete(self, incident_id: uuid.UUID, *, tenant_id: uuid.UUID) -> None:
        """Permanently delete incident. CLI-only operation."""
        result = await self._session.execute(
            select(IncidentModel).where(IncidentModel.id == incident_id)
        )
        model = result.scalar_one_or_none()
        if model is not None:
            await self._session.delete(model)
            await self._session.commit()

    async def list(
        self,
        *,
        tenant_id: uuid.UUID | None = None,
        category: IncidentCategory | None = None,
        severity: IncidentSeverity | None = None,
        limit: int = 50,
        offset: int = 0,
        include_deleted: bool = False,
    ) -> list[IncidentEntity]:
        """List incidents with optional filtering and pagination."""
        stmt = select(IncidentModel)

        if not include_deleted:
            stmt = stmt.where(IncidentModel.deleted_at.is_(None))

        if tenant_id is not None:
            stmt = stmt.where(
                or_(
                    IncidentModel.tenant_id == tenant_id,
                    IncidentModel.tenant_id.is_(None),
                )
            )

        if category is not None:
            stmt = stmt.where(IncidentModel.category == str(category.value))

        if severity is not None:
            stmt = stmt.where(IncidentModel.severity == str(severity.value))

        stmt = stmt.order_by(IncidentModel.created_at.desc()).limit(limit).offset(offset)

        result = await self._session.execute(stmt)
        return [_model_to_entity(m) for m in result.scalars().all()]

    async def count(
        self,
        *,
        tenant_id: uuid.UUID | None = None,
        category: IncidentCategory | None = None,
        severity: IncidentSeverity | None = None,
        include_deleted: bool = False,
    ) -> int:
        """Count incidents matching the given filters (for pagination)."""
        from sqlalchemy import func

        stmt = select(func.count(IncidentModel.id))

        if not include_deleted:
            stmt = stmt.where(IncidentModel.deleted_at.is_(None))

        if tenant_id is not None:
            stmt = stmt.where(
                or_(
                    IncidentModel.tenant_id == tenant_id,
                    IncidentModel.tenant_id.is_(None),
                )
            )

        if category is not None:
            stmt = stmt.where(IncidentModel.category == str(category.value))

        if severity is not None:
            stmt = stmt.where(IncidentModel.severity == str(severity.value))

        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def search(
        self,
        query: str,
        *,
        tenant_id: uuid.UUID | None = None,
        limit: int = 20,
    ) -> list[IncidentEntity]:
        """Full-text search over title, anti_pattern, and remediation (ILIKE)."""
        pattern = f"%{query}%"
        stmt = select(IncidentModel).where(
            IncidentModel.deleted_at.is_(None),
            or_(
                IncidentModel.title.ilike(pattern),
                IncidentModel.anti_pattern.ilike(pattern),
                IncidentModel.remediation.ilike(pattern),
            ),
        )

        if tenant_id is not None:
            stmt = stmt.where(
                or_(
                    IncidentModel.tenant_id == tenant_id,
                    IncidentModel.tenant_id.is_(None),
                )
            )

        stmt = stmt.order_by(IncidentModel.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return [_model_to_entity(m) for m in result.scalars().all()]
