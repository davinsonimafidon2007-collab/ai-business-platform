"""Shared fixtures for persistence layer integration tests.

Uses a temporary SQLite database (aiosqlite) to test all repository
operations. No real PostgreSQL required.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.manager import DatabaseManager
from app.models.base import Base
from app.models.cached_market import CachedMarketData  # noqa: F401
from app.models.opportunity import Opportunity  # noqa: F401
from app.models.search_history import SearchHistory  # noqa: F401
from app.models.vehicle import Vehicle  # noqa: F401
from app.repositories.cached_market_repository import CachedMarketRepository
from app.repositories.opportunity_repository import OpportunityRepository
from app.repositories.search_history_repository import SearchHistoryRepository


@pytest_asyncio.fixture
async def db_manager() -> AsyncGenerator[DatabaseManager]:
    """Creates a DatabaseManager with an in-memory SQLite database.

    Creates all tables before yielding and disposes after.
    """
    manager = DatabaseManager(
        "sqlite+aiosqlite://",
        echo=False,
    )
    async with manager._engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield manager
    await manager.shutdown()


@pytest_asyncio.fixture
async def session(
    db_manager: DatabaseManager,
) -> AsyncGenerator[AsyncSession]:
    """Provides an async session for testing."""
    async with db_manager.session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


@pytest_asyncio.fixture
async def search_history_repo(
    session: AsyncSession,
) -> SearchHistoryRepository:
    """Provides a SearchHistoryRepository with a clean session."""
    return SearchHistoryRepository(session)


@pytest_asyncio.fixture
async def opportunity_repo(
    session: AsyncSession,
) -> OpportunityRepository:
    """Provides an OpportunityRepository with a clean session."""
    return OpportunityRepository(session)


@pytest_asyncio.fixture
async def cached_market_repo(
    session: AsyncSession,
) -> CachedMarketRepository:
    """Provides a CachedMarketRepository with a clean session."""
    return CachedMarketRepository(session)


@pytest_asyncio.fixture
async def sample_vehicle(session: AsyncSession) -> Vehicle:
    """Creates and persists a sample Vehicle for testing.

    Many repositories reference vehicles via FK, so we need a vehicle
    in the database before testing opportunity or evaluation repos.
    """
    vehicle = Vehicle(
        user_id="00000000-0000-0000-0000-000000000099",
        source="test_provider",
        external_id="test_ext_123",
        brand="TestBrand",
        model="TestModel",
        price=15000.0,
        currency="EUR",
    )
    session.add(vehicle)
    await session.commit()
    await session.refresh(vehicle)
    return vehicle

