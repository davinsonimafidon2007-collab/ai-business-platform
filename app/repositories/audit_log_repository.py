from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


class AuditLogRepository:
    """Audit log repository - create and read only (immutable)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, audit_log: AuditLog) -> AuditLog:
        self.session.add(audit_log)
        await self.session.commit()
        await self.session.refresh(audit_log)
        return audit_log

    async def get_by_id(self, log_id: str) -> AuditLog | None:
        result = await self.session.execute(
            select(AuditLog).where(AuditLog.id == log_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_id(
        self,
        user_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        result = await self.session.execute(
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_by_action(
        self,
        action: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        result = await self.session.execute(
            select(AuditLog)
            .where(AuditLog.action == action)
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_by_resource(
        self,
        resource: str,
        resource_id: str | None = None,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        query = select(AuditLog).where(AuditLog.resource == resource)
        if resource_id:
            query = query.where(AuditLog.resource_id == resource_id)
        result = await self.session.execute(
            query.order_by(AuditLog.timestamp.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def get_recent(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        since: datetime | None = None,
    ) -> list[AuditLog]:
        query = select(AuditLog)
        if since:
            query = query.where(AuditLog.timestamp >= since)
        result = await self.session.execute(
            query.order_by(AuditLog.timestamp.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def count_by_action_since(
        self,
        action: str,
        since: datetime,
    ) -> int:
        result = await self.session.execute(
            select(AuditLog).where(
                AuditLog.action == action,
                AuditLog.timestamp >= since,
            )
        )
        return len(result.scalars().all())
