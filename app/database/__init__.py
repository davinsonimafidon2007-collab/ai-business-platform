"""Database layer — single entrypoint.

Usage:
    from app.database import db_manager, get_db_session, DatabaseManager
    from app.database.session import AsyncSessionLocal
"""
from app.database.manager import DatabaseManager
from app.database.session import AsyncSessionLocal, db_manager, get_db_session

__all__ = [
    "DatabaseManager",
    "AsyncSessionLocal",
    "db_manager",
    "get_db_session",
]

