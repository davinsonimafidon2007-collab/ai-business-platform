"""Integration tests for DatabaseManager.

Verifies the lifecycle management (init, shutdown, session creation)
using an in-memory SQLite database.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.manager import DatabaseManager
from app.models.base import Base


class TestDatabaseManager:
    """Test suite for DatabaseManager."""

    @pytest.mark.asyncio
    async def test_create_manager(self) -> None:
        """A DatabaseManager can be created with a SQLite URL."""
        manager = DatabaseManager("sqlite+aiosqlite://")
        assert manager is not None
        assert manager.engine is not None
        assert manager.session_factory is not None
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_init_creates_tables(self) -> None:
        """Calling init() creates all tables defined in Base.metadata."""
        manager = DatabaseManager("sqlite+aiosqlite://")
        await manager.init()

        # Verify tables exist by executing a raw query
        async with manager.engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                    "ORDER BY name"
                )
            )
            tables = [row[0] for row in result]

        assert "vehicles" in tables
        assert "searches" in tables
        assert "search_history" in tables
        assert "opportunities" in tables
        assert "cached_market_data" in tables

        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_init_idempotent(self) -> None:
        """Calling init() multiple times does not raise errors."""
        manager = DatabaseManager("sqlite+aiosqlite://")
        await manager.init()
        await manager.init()  # second call should be safe
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_shutdown_disposes_engine(self) -> None:
        """After shutdown, engine is disposed (no new connections possible)."""
        manager = DatabaseManager("sqlite+aiosqlite://")
        await manager.init()
        await manager.shutdown()
        # Engine dispose is idempotent
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_get_session_yields_active_session(self) -> None:
        """get_session() yields an active AsyncSession."""
        manager = DatabaseManager("sqlite+aiosqlite://")
        await manager.init()

        async with manager.get_session() as session:
            assert isinstance(session, AsyncSession)
            assert session.is_active

        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_create_session_manual(self) -> None:
        """create_session() returns an independent session."""
        manager = DatabaseManager("sqlite+aiosqlite://")
        await manager.init()

        session = await manager.create_session()
        assert isinstance(session, AsyncSession)
        assert session.is_active
        await session.close()

        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_can_execute_queries(self) -> None:
        """Queries can be executed through the session."""
        manager = DatabaseManager("sqlite+aiosqlite://")
        await manager.init()

        async with manager.get_session() as session:
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1

        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_context_manager_support(self) -> None:
        """DatabaseManager supports async context manager protocol."""
        async with DatabaseManager("sqlite+aiosqlite://") as manager:
            assert manager.engine is not None

            async with manager.get_session() as session:
                result = await session.execute(text("SELECT 1"))
                assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_tables_created_with_correct_columns(self) -> None:
        """Verify that new tables have expected columns."""
        manager = DatabaseManager("sqlite+aiosqlite://")
        await manager.init()

        async with manager.engine.connect() as conn:
            # Check search_history columns
            result = await conn.execute(
                text("PRAGMA table_info(search_history)")
            )
            columns = {row[1] for row in result}
            assert "id" in columns
            assert "query" in columns
            assert "timestamp" in columns
            assert "providers_used" in columns
            assert "results_count" in columns
            assert "execution_time" in columns

            # Check opportunities columns
            result = await conn.execute(
                text("PRAGMA table_info(opportunities)")
            )
            columns = {row[1] for row in result}
            assert "id" in columns
            assert "vehicle_id" in columns
            assert "opportunity_score" in columns
            assert "recommendation" in columns
            assert "roi" in columns
            assert "risk" in columns
            assert "profit" in columns
            assert "analyzed_at" in columns
            assert "engine_version" in columns

            # Check cached_market_data columns
            result = await conn.execute(
                text("PRAGMA table_info(cached_market_data)")
            )
            columns = {row[1] for row in result}
            assert "id" in columns
            assert "external_id" in columns
            assert "provider" in columns
            assert "market_hash" in columns
            assert "market_price" in columns
            assert "confidence" in columns
            assert "expires_at" in columns

        await manager.shutdown()

