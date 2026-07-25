from __future__ import annotations

from uuid import UUID

from app.models.search import Search
from app.repositories.search_repository import SearchRepository


class SearchService:
    def __init__(self, repository: SearchRepository) -> None:
        self.repository = repository

    async def create_search(self, data: dict) -> Search:
        search = Search(**data)
        return await self.repository.create(search)

    async def get_search(self, search_id: str | UUID) -> Search | None:
        return await self.repository.get_by_id(search_id)

    async def list_searches(self, skip: int = 0, limit: int = 100) -> list[Search]:
        return await self.repository.list_all(skip=skip, limit=limit)

    async def update_search(self, search: Search, data: dict) -> Search:
        for key, value in data.items():
            if value is not None:
                setattr(search, key, value)
        return await self.repository.update(search)

    async def delete_search(self, search: Search) -> None:
        await self.repository.delete(search)