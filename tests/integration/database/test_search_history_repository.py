"""Integration tests for SearchHistoryRepository.

Verifies CRUD operations for search history records against a
temporary SQLite database.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.search_history import SearchHistory
from app.repositories.search_history_repository import SearchHistoryRepository


class TestSearchHistoryRepository:
    """Test suite for SearchHistoryRepository."""

    @pytest.mark.asyncio
    async def test_save_creates_record(
        self,
        search_history_repo: SearchHistoryRepository,
        session: AsyncSession,
    ) -> None:
        """A search history record can be saved and retrieved."""
        record = SearchHistory(
            query="BMW 320d",
            providers_used='["mobile_de", "autoscout24"]',
            results_count=15,
            execution_time=2.5,
        )
        saved = await search_history_repo.save(record)
        assert saved.id is not None
        assert saved.query == "BMW 320d"
        assert saved.results_count == 15
        assert saved.execution_time == 2.5
        assert saved.timestamp is not None

    @pytest.mark.asyncio
    async def test_get_returns_record(
        self,
        search_history_repo: SearchHistoryRepository,
    ) -> None:
        """A saved record can be retrieved by id."""
        record = SearchHistory(
            query="Audi A4",
            providers_used='["mobile_de"]',
            results_count=8,
            execution_time=1.2,
        )
        saved = await search_history_repo.save(record)
        retrieved = await search_history_repo.get(saved.id)
        assert retrieved is not None
        assert retrieved.id == saved.id
        assert retrieved.query == "Audi A4"

    @pytest.mark.asyncio
    async def test_get_returns_none_for_missing(
        self,
        search_history_repo: SearchHistoryRepository,
    ) -> None:
        """get() returns None when id does not exist."""
        result = await search_history_repo.get("non-existent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_query(
        self,
        search_history_repo: SearchHistoryRepository,
    ) -> None:
        """Records can be retrieved by query text."""
        await search_history_repo.save(
            SearchHistory(query="BMW X5", results_count=5)
        )
        await search_history_repo.save(
            SearchHistory(query="BMW 320d", results_count=10)
        )
        await search_history_repo.save(
            SearchHistory(query="Audi Q5", results_count=3)
        )

        results = await search_history_repo.get_by_query("BMW")
        assert len(results) == 2
        assert all("BMW" in r.query for r in results)

    @pytest.mark.asyncio
    async def test_list_returns_paginated(
        self,
        search_history_repo: SearchHistoryRepository,
    ) -> None:
        """Records are returned with pagination, newest first."""
        for i in range(10):
            await search_history_repo.save(
                SearchHistory(
                    query=f"Search {i}",
                    timestamp=datetime.now(UTC),
                )
            )

        all_records = await search_history_repo.list(skip=0, limit=100)
        assert len(all_records) == 10

        page1 = await search_history_repo.list(skip=0, limit=3)
        assert len(page1) == 3

        page2 = await search_history_repo.list(skip=3, limit=3)
        assert len(page2) == 3

        # Verify ordering: newest first
        assert page1[0].timestamp >= page1[-1].timestamp

    @pytest.mark.asyncio
    async def test_delete_removes_record(
        self,
        search_history_repo: SearchHistoryRepository,
    ) -> None:
        """A record can be deleted."""
        record = SearchHistory(query="Test delete")
        saved = await search_history_repo.save(record)

        await search_history_repo.delete(saved)
        retrieved = await search_history_repo.get(saved.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_count(
        self,
        search_history_repo: SearchHistoryRepository,
    ) -> None:
        """count() returns the total number of records."""
        assert await search_history_repo.count() == 0

        await search_history_repo.save(SearchHistory(query="Q1"))
        await search_history_repo.save(SearchHistory(query="Q2"))
        assert await search_history_repo.count() == 2

    @pytest.mark.asyncio
    async def test_save_with_all_fields(
        self,
        search_history_repo: SearchHistoryRepository,
    ) -> None:
        """All fields are persisted correctly."""
        now = datetime.now(UTC)
        record = SearchHistory(
            query="Mercedes C220",
            timestamp=now,
            providers_used='["mobile_de"]',
            results_count=22,
            execution_time=3.14,
        )
        saved = await search_history_repo.save(record)
        assert saved.query == "Mercedes C220"
        assert saved.timestamp.timestamp() == pytest.approx(
            now.timestamp(), rel=1e-3
        )
        assert saved.providers_used == '["mobile_de"]'
        assert saved.results_count == 22
        assert saved.execution_time == 3.14

