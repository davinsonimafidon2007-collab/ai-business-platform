"""FeatureFlag repository — TASK-012.

Repositorio CRUD mínimo sobre la tabla ``feature_flags``. El caching con
Redis vive en el service, no aquí.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feature_flag import FeatureFlag


class FeatureFlagRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_key(self, key: str) -> FeatureFlag | None:
        result = await self.session.execute(
            select(FeatureFlag).where(FeatureFlag.key == key)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[FeatureFlag]:
        result = await self.session.execute(
            select(FeatureFlag).order_by(FeatureFlag.key)
        )
        return list(result.scalars().all())

    async def create(self, flag: FeatureFlag) -> FeatureFlag:
        self.session.add(flag)
        await self.session.commit()
        await self.session.refresh(flag)
        return flag

    async def update(self, flag: FeatureFlag) -> FeatureFlag:
        self.session.add(flag)
        await self.session.commit()
        await self.session.refresh(flag)
        return flag

    async def delete(self, flag: FeatureFlag) -> None:
        await self.session.delete(flag)
        await self.session.commit()