"""DatabaseManager — Thin wrapper around SQLAlchemy async session infrastructure.

Provides lifecycle management (init, shutdown) for testability while keeping
a single engine + session factory as the canonical database layer.
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

logger = logging.getLogger(__name__)


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

    Note:
        Acepta config de pool SQLAlchemy estándar: ``pool_size``,
        ``max_overflow``, ``pool_timeout``, ``pool_pre_ping``. Cuando se usan
        con ``asyncpg`` se traducen a las opciones del pool nativo de la librería.
    """

    def __init__(
        self,
        database_url: str,
        echo: bool = False,
        *,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: float = 30.0,
        pool_pre_ping: bool = True,
        **engine_kwargs: Any,
    ) -> None:
        self._database_url = database_url
        self._pool_size = pool_size
        self._max_overflow = max_overflow
        self._pool_timeout = pool_timeout
        # Los parámetros de pool (QueuePool) son específicos de dialectos tipo
        # Postgres; SQLite usa StaticPool/SingletonThreadPool y los rechaza.
        engine_kwargs = {
            **engine_kwargs,
            **(
                {
                    "pool_size": pool_size,
                    "max_overflow": max_overflow,
                    "pool_timeout": pool_timeout,
                    "pool_pre_ping": pool_pre_ping,
                }
                if not database_url.startswith("sqlite")
                else {}
            ),
        }
        self._engine = create_async_engine(
            database_url,
            echo=echo,
            **engine_kwargs,
        )
        self._session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self._engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )
        self._last_checkout_ts: dict[object, float] = {}
        self._connect_pool_logging()

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

    def _connect_pool_logging(self) -> None:
        """Conecta listeners de eventos del pool para observar saturación.

        TASK-011: mide cuánto tarda cada ``checkout`` del pool (espera por una
        conexión libre). Si la espera supera ``pool_timeout`` (la conexión se
        va a desechar) se loguea un warning con la URL y el uso del pool.
        """
        from sqlalchemy import event

        pool = self._engine.pool
        start_times: dict[object, float] = self._last_checkout_ts

        def _checkedout() -> int:
            try:
                return int(pool.checkedout())
            except (AttributeError, NotImplementedError):
                return -1

        def _pool_size() -> int:
            try:
                return int(pool.size())
            except (AttributeError, NotImplementedError):
                return -1

        @event.listens_for(pool, "checkout")
        def _on_checkout(dbapi_conn: object, conn_record: Any, conn_proxy: Any) -> None:
            start_times[dbapi_conn] = time.monotonic()

        @event.listens_for(pool, "checkin")
        def _on_checkin(dbapi_conn: object, conn_record: Any) -> None:
            started = start_times.pop(dbapi_conn, None)
            if started is None:
                return
            wait = time.monotonic() - started
            checkedout = _checkedout()
            if wait > self._pool_timeout * 0.9:
                logger.warning(
                    "DB pool: checkout esperó %.2fs (timeout=%.1fs) para %s. "
                    "checkedout=%s — posible saturación del pool",
                    wait,
                    self._pool_timeout,
                    self._database_url,
                    checkedout,
                )
            elif wait > 0.5:
                logger.info(
                    "DB pool: checkout lento %.2fs para %s (checkedout=%s)",
                    wait,
                    self._database_url,
                    checkedout,
                )

        # El evento "connect" marca el momento de apertura de cada socket.
        @event.listens_for(pool, "connect")
        def _on_connect(dbapi_conn: object, connection_record: Any) -> None:
            logger.debug(
                "DB pool: nueva conexión abierta (checkedout=%s, tamaño=%s)",
                _checkedout(),
                _pool_size(),
            )

    async def pool_stats(self) -> dict[str, Any]:
        """Devuelve métricas del pool (TASK-011): conexiones en uso, libres, etc.

        Útil para el panel de administración y para diagnosticar saturación.
        """
        pool = self._engine.pool
        try:
            checkedout = pool.checkedout()
            size = pool.size()
            overflow = pool.overflow()
        except Exception:  # pool nativo asyncpg expone API distinta
            return {"available": False}

        return {
            "available": True,
            "pool_size": self._pool_size,
            "max_overflow": self._max_overflow,
            "checkedout": checkedout,
            "size": size,
            "overflow": overflow,
            "limit": self._pool_size + self._max_overflow,
            "saturated": checkedout >= (self._pool_size + self._max_overflow),
        }

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
    async def get_session(self) -> AsyncGenerator[AsyncSession]:
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

