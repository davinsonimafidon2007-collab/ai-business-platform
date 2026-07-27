from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import ApiKey


class ApiKeyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, api_key: ApiKey) -> ApiKey:
        self.session.add(api_key)
        await self.session.commit()
        await self.session.refresh(api_key)
        return api_key

    async def get_by_id(self, api_key_id: str) -> ApiKey | None:
        result = await self.session.execute(
            select(ApiKey).where(ApiKey.id == api_key_id)
        )
        return result.scalar_one_or_none()

    async def get_by_prefix(self, prefix: str) -> ApiKey | None:
        result = await self.session.execute(
            select(ApiKey).where(ApiKey.prefix == prefix)
        )
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: str) -> list[ApiKey]:
        result = await self.session.execute(
            select(ApiKey).where(ApiKey.user_id == user_id).order_by(ApiKey.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_active_by_key_hash(self, key_hash: str) -> ApiKey | None:
        result = await self.session.execute(
            select(ApiKey).where(
                ApiKey.key_hash == key_hash,
                ApiKey.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def deactivate(self, api_key_id: str) -> None:
        await self.session.execute(
            update(ApiKey)
            .where(ApiKey.id == api_key_id)
            .values(is_active=False)
        )
        await self.session.commit()

    async def update_last_used(self, api_key_id: str) -> None:
        await self.session.execute(
            update(ApiKey)
            .where(ApiKey.id == api_key_id)
            .values(last_used_at=datetime.now(timezone.utc))
        )
        await self.session.commit()

    async def list_active_by_user_id(self, user_id: str) -> list[ApiKey]:
        result = await self.session.execute(
            select(ApiKey).where(
                ApiKey.user_id == user_id,
                ApiKey.is_active == True,
            ).order_by(ApiKey.created_at.desc())
        )
        return list(result.scalars().all())
