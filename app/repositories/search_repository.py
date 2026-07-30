from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.search import Search


class SearchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, search: Search) -> Search:
        self.session.add(search)
        await self.session.commit()
        await self.session.refresh(search)
        return search

    async def get_by_id(self, search_id: str | UUID) -> Search | None:
        result = await self.session.execute(select(Search).where(Search.id == str(search_id)))
        return result.scalar_one_or_none()

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[Search]:
        result = await self.session.execute(select(Search).order_by(Search.created_at.desc()).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def list_by_user(self, user_id: str, skip: int = 0, limit: int = 100) -> list[Search]:
        result = await self.session.execute(
            select(Search)
            .where(Search.user_id == str(user_id))
            .order_by(Search.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update(self, search: Search) -> Search:
        await self.session.commit()
        await self.session.refresh(search)
        return search

    async def delete(self, search: Search) -> None:
        await self.session.delete(search)
        await self.session.commit()