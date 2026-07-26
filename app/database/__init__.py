"""Database layer package.

Provides the DatabaseManager as a thin wrapper around the existing
session infrastructure in app/db/session.py, plus repositories for
persistence operations.

Usage:
    manager = DatabaseManager("sqlite+aiosqlite:///test.db")
    await manager.init()
    async with manager.get_session() as session:
        repo = SomeRepository(session)
        ...
    await manager.shutdown()
"""

from app.database.manager import DatabaseManager

__all__ = ["DatabaseManager"]

