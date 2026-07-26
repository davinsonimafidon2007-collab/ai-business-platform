from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.search_history import SearchHistory


class SearchHistoryRepository:
    """Repository for SearchHistory persistence operations.

    Handles CRUD for search execution history records,
    used for auditing, analytics and debugging.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, search_history: SearchHistory) -> SearchHistory:
        """Persists a new search history record.

        Args:
            search_history: The SearchHistory instance to persist.

        Returns:
            The persisted SearchHistory with generated id and timestamps.
        """
        self.session.add(search_history)
        await self.session.commit()
        await self.session.refresh(search_history)
        return search_history

    async def get(self, history_id: str | UUID) -> SearchHistory | None:
        """Retrieves a search history record by id.

        Args:
            history_id: The UUID (as string or UUID object) of the record.

        Returns:
            The SearchHistory if found, None otherwise.
        """
        result = await self.session.execute(
            select(SearchHistory).where(SearchHistory.id == str(history_id))
        )
        return result.scalar_one_or_none()

    async def get_by_query(
        self,
        query: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SearchHistory]:
        """Retrieves search history records by query term.

        Args:
            query: The search query text to filter by.
            skip: Number of records to skip (pagination).
            limit: Maximum number of records to return.

        Returns:
            List of matching SearchHistory records ordered by timestamp DESC.
        """
        result = await self.session.execute(
            select(SearchHistory)
            .where(SearchHistory.query.ilike(f"%{query}%"))
            .order_by(SearchHistory.timestamp.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SearchHistory]:
        """Lists all search history records with pagination.

        Args:
            skip: Number of records to skip (pagination).
            limit: Maximum number of records to return.

        Returns:
            List of SearchHistory records ordered by timestamp DESC.
        """
        result = await self.session.execute(
            select(SearchHistory)
            .order_by(SearchHistory.timestamp.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def delete(self, search_history: SearchHistory) -> None:
        """Deletes a search history record.

        Args:
            search_history: The SearchHistory instance to delete.
        """
        await self.session.delete(search_history)
        await self.session.commit()

    async def count(self) -> int:
        """Counts total search history records.

        Returns:
            Total number of records.
        """
        result = await self.session.execute(
            select(func.count(SearchHistory.id))
        )
        return result.scalar() or 0

