"""DatabaseManager — Thin wrapper around SQLAlchemy async session infrastructure.

Reuses the existing engine/sessionmaker patterns from app/db/session.py
while adding lifecycle management (init, shutdown) for testability.

The manager is designed to work with any async SQLAlchemy-compatible driver
(aiosqlite for development/testing, asyncpg for production).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.models.base import Base


class DatabaseManager:
    """Gestiona el ciclo de vida de la conexión a la base de datos.

    Es un wrapper fino que envuelve la configuración de engine y sessionmaker,
    permitiendo inicialización, creación de tablas y cierre controlado.

    Compatible con SQLite (aiosqlite) para testing y PostgreSQL (asyncpg)
    para producción.

    Args:
        database_url: URL de conexión SQLAlchemy asíncrona.
        echo: Si True, habilita logging de SQL (por defecto False).
        engine_kwargs: Argumentos adicionales para create_async_engine.

    Example:
        manager = DatabaseManager("sqlite+aiosqlite:///test.db")
        await manager.init()
        async with manager.get_session() as session:
            # operaciones con la sesión
            ...
        await manager.shutdown()
    """

    def __init__(
        self,
        database_url: str,
        echo: bool = False,
        **engine_kwargs: Any,
    ) -> None:
        self._database_url = database_url
        self._engine = create_async_engine(database_url, echo=echo, **engine_kwargs)
        self._session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self._engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------

    @property
    def engine(self) -> Any:
        """El engine SQLAlchemy subyacente."""
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """El sessionmaker para crear sesiones."""
        return self._session_factory

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    async def init(self) -> None:
        """Inicializa la conexión a la base de datos.

        Verifica que la conexión sea válida. Las tablas son gestionadas
        exclusivamente por Alembic mediante migraciones.
        """
        # Verify connection is working
        async with self._engine.connect() as conn:
            await conn.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )

    async def shutdown(self) -> None:
        """Cierra la conexión a la base de datos.

        Libera todos los recursos del engine. Es seguro llamarlo
        incluso si el engine ya fue cerrado.
        """
        await self._engine.dispose()

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Obtiene una sesión asíncrona como context manager.

        Yields:
            AsyncSession: Sesión SQLAlchemy asíncrona.

        Example:
            async with manager.get_session() as session:
                result = await session.execute(select(MyModel))
        """
        async with self._session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

    async def create_session(self) -> AsyncSession:
        """Crea una nueva sesión independiente.

        Útil cuando se necesita una sesión fuera de un context manager.
        El llamante es responsable de cerrar la sesión.

        Returns:
            AsyncSession: Nueva sesión asíncrona.
        """
        return self._session_factory()

    # ------------------------------------------------------------------
    # Métodos de conveniencia
    # ------------------------------------------------------------------

    async def __aenter__(self) -> DatabaseManager:
        """Soporte para async with."""
        await self.init()
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc_val: object,
        exc_tb: object,
    ) -> None:
        """Limpieza al salir del context manager."""
        await self.shutdown()

