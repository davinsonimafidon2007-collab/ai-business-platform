"""Database session management (canonical entrypoint).

Shared DatabaseManager instance + FastAPI dependency.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.manager import DatabaseManager

db_manager = DatabaseManager(settings.database_url, echo=False)
AsyncSessionLocal = db_manager.session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session."""
    async with db_manager.get_session() as session:
        yield session
