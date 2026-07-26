"""Integration tests for CachedMarketRepository.

Verifies CRUD operations for cached market data against a
temporary SQLite database.

The cache is keyed by (external_id, provider, market_hash) and
does NOT depend on the vehicles table.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.cached_market import CachedMarketData
from app.repositories.cached_market_repository import CachedMarketRepository


class TestCachedMarketRepository:
    """Test suite for CachedMarketRepository."""

    @pytest.mark.asyncio
    async def test_save_creates_entry(
        self,
        cached_market_repo: CachedMarketRepository,
    ) -> None:
        """A cached market data entry can be saved."""
        entry = CachedMarketData(
            external_id="ext_001",
            provider="mobile_de",
            market_hash="abc123",
            market_price=20000.0,
            confidence=85.0,
            supply_level=45.0,
            demand_level=70.0,
            market_trend="rising",
            comparable_count=12,
            notes='{"source": "comparable_market"}',
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        saved = await cached_market_repo.save(entry)
        assert saved.id is not None
        assert saved.external_id == "ext_001"
        assert saved.provider == "mobile_de"
        assert saved.market_price == 20000.0
        assert saved.confidence == 85.0
        assert saved.market_trend == "rising"

    @pytest.mark.asyncio
    async def test_save_many(
        self,
        cached_market_repo: CachedMarketRepository,
    ) -> None:
        """Multiple entries can be saved at once."""
        entries = [
            CachedMarketData(
                external_id="ext_001",
                provider="mobile_de",
                market_price=20000.0,
                confidence=80.0,
            ),
            CachedMarketData(
                external_id="ext_002",
                provider="autoscout24",
                market_price=18000.0,
                confidence=75.0,
            ),
        ]
        saved = await cached_market_repo.save_many(entries)
        assert len(saved) == 2
        assert all(e.id is not None for e in saved)

    @pytest.mark.asyncio
    async def test_get_returns_entry(
        self,
        cached_market_repo: CachedMarketRepository,
    ) -> None:
        """A saved entry can be retrieved by id."""
        entry = CachedMarketData(
            external_id="ext_001",
            provider="mobile_de",
            market_price=20000.0,
        )
        saved = await cached_market_repo.save(entry)
        retrieved = await cached_market_repo.get(saved.id)
        assert retrieved is not None
        assert retrieved.id == saved.id
        assert retrieved.market_price == 20000.0

    @pytest.mark.asyncio
    async def test_get_returns_none_for_missing(
        self,
        cached_market_repo: CachedMarketRepository,
    ) -> None:
        """get() returns None when id does not exist."""
        result = await cached_market_repo.get("non-existent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_external_id(
        self,
        cached_market_repo: CachedMarketRepository,
    ) -> None:
        """Entries can be retrieved by external_id and provider."""
        entry = CachedMarketData(
            external_id="ext_001",
            provider="mobile_de",
            market_price=20000.0,
        )
        await cached_market_repo.save(entry)

        results = await cached_market_repo.get_by_external_id(
            "ext_001", "mobile_de"
        )
        assert len(results) == 1
        assert results[0].market_price == 20000.0

        # Different provider should return empty
        results2 = await cached_market_repo.get_by_external_id(
            "ext_001", "autoscout24"
        )
        assert len(results2) == 0

    @pytest.mark.asyncio
    async def test_get_valid_returns_non_expired(
        self,
        cached_market_repo: CachedMarketRepository,
    ) -> None:
        """get_valid() only returns non-expired entries."""
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        entry = CachedMarketData(
            external_id="ext_001",
            provider="mobile_de",
            market_hash="hash1",
            market_price=20000.0,
            expires_at=future,
        )
        await cached_market_repo.save(entry)

        valid = await cached_market_repo.get_valid(
            "ext_001", "mobile_de", "hash1"
        )
        assert valid is not None
        assert valid.market_price == 20000.0

    @pytest.mark.asyncio
    async def test_get_valid_returns_none_for_expired(
        self,
        cached_market_repo: CachedMarketRepository,
    ) -> None:
        """get_valid() returns None for expired entries."""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        entry = CachedMarketData(
            external_id="ext_001",
            provider="mobile_de",
            market_hash="hash1",
            market_price=20000.0,
            expires_at=past,
        )
        await cached_market_repo.save(entry)

        valid = await cached_market_repo.get_valid(
            "ext_001", "mobile_de", "hash1"
        )
        assert valid is None

    @pytest.mark.asyncio
    async def test_get_valid_without_hash(
        self,
        cached_market_repo: CachedMarketRepository,
    ) -> None:
        """get_valid() works without market_hash."""
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        entry = CachedMarketData(
            external_id="ext_001",
            provider="mobile_de",
            market_price=20000.0,
            expires_at=future,
        )
        await cached_market_repo.save(entry)

        valid = await cached_market_repo.get_valid("ext_001", "mobile_de")
        assert valid is not None

    @pytest.mark.asyncio
    async def test_exists(
        self,
        cached_market_repo: CachedMarketRepository,
    ) -> None:
        """exists() checks if an entry exists for the given key."""
        assert (
            await cached_market_repo.exists("ext_001", "mobile_de")
        ) is False

        entry = CachedMarketData(
            external_id="ext_001",
            provider="mobile_de",
            market_hash="hash1",
            market_price=20000.0,
        )
        await cached_market_repo.save(entry)

        assert (
            await cached_market_repo.exists("ext_001", "mobile_de") is True
        )
        assert (
            await cached_market_repo.exists("ext_001", "mobile_de", "hash1")
            is True
        )
        assert (
            await cached_market_repo.exists("ext_001", "mobile_de", "hash2")
            is False
        )

    @pytest.mark.asyncio
    async def test_list_returns_paginated(
        self,
        cached_market_repo: CachedMarketRepository,
    ) -> None:
        """Entries are returned with pagination."""
        for i in range(5):
            await cached_market_repo.save(
                CachedMarketData(
                    external_id=f"ext_{i}",
                    provider="mobile_de",
                    market_price=float(10000 + i * 1000),
                )
            )

        all_entries = await cached_market_repo.list(skip=0, limit=100)
        assert len(all_entries) == 5

        page1 = await cached_market_repo.list(skip=0, limit=2)
        assert len(page1) == 2

        page2 = await cached_market_repo.list(skip=2, limit=2)
        assert len(page2) == 2

    @pytest.mark.asyncio
    async def test_delete_expired(
        self,
        cached_market_repo: CachedMarketRepository,
    ) -> None:
        """delete_expired() removes all expired entries."""
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        past = datetime.now(timezone.utc) - timedelta(hours=1)

        valid = CachedMarketData(
            external_id="ext_valid",
            provider="mobile_de",
            market_price=20000.0,
            expires_at=future,
        )
        expired = CachedMarketData(
            external_id="ext_expired",
            provider="mobile_de",
            market_price=15000.0,
            expires_at=past,
        )
        await cached_market_repo.save(valid)
        await cached_market_repo.save(expired)

        deleted_count = await cached_market_repo.delete_expired()
        assert deleted_count == 1

        # Valid entry should still exist
        assert (
            await cached_market_repo.exists("ext_valid", "mobile_de")
        ) is True

        # Expired entry should be gone
        assert (
            await cached_market_repo.exists("ext_expired", "mobile_de")
        ) is False

    @pytest.mark.asyncio
    async def test_delete_removes_entry(
        self,
        cached_market_repo: CachedMarketRepository,
    ) -> None:
        """An entry can be deleted."""
        entry = CachedMarketData(
            external_id="ext_001",
            provider="mobile_de",
            market_price=20000.0,
        )
        saved = await cached_market_repo.save(entry)
        await cached_market_repo.delete(saved)
        assert await cached_market_repo.get(saved.id) is None

    @pytest.mark.asyncio
    async def test_count(
        self,
        cached_market_repo: CachedMarketRepository,
    ) -> None:
        """count() returns total number of entries."""
        assert await cached_market_repo.count() == 0
        await cached_market_repo.save(
            CachedMarketData(
                external_id="ext_001", provider="mobile_de", market_price=20000.0
            )
        )
        assert await cached_market_repo.count() == 1

    @pytest.mark.asyncio
    async def test_does_not_depend_on_vehicles_table(
        self,
        cached_market_repo: CachedMarketRepository,
    ) -> None:
        """Cached market data can be saved without a vehicle existing.

        This is a key design requirement: cache entries use (external_id, provider)
        as key, NOT a FK to the vehicles table.
        """
        entry = CachedMarketData(
            external_id="external_only_001",
            provider="mobile_de",
            market_price=22000.0,
            confidence=90.0,
        )
        saved = await cached_market_repo.save(entry)
        assert saved.id is not None
        assert saved.external_id == "external_only_001"

        # Should be retrievable without any vehicle reference
        retrieved = await cached_market_repo.get_valid(
            "external_only_001", "mobile_de"
        )
        assert retrieved is not None
        assert retrieved.market_price == 22000.0

