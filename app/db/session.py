"""Database session management.

Provides a shared DatabaseManager instance and a FastAPI dependency
for obtaining async database sessions. All components (routes, middleware,
scheduler) use the same engine and session factory.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.manager import DatabaseManager

# Shared DatabaseManager instance — single engine, single session factory
from app.core.config import settings

db_manager = DatabaseManager(settings.database_url, echo=False)

# Re-export AsyncSessionLocal for backward compatibility with middleware
AsyncSessionLocal = db_manager.session_factory


async def get_db_session() -> AsyncSession:
    """FastAPI dependency that yields an async database session."""
    async with db_manager.get_session() as session:
        yield session
