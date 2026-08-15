"""FeatureFlag service with Redis cache — TASK-012.

Cache L1: Redis TTL 60s. Si Redis cae, lee de DB (fail-soft).

Nota: ``app.core.redis.get_redis`` crea el cliente con
``decode_responses=True``, así que ``get()`` devuelve ``str`` (nunca
``bytes``). La lógica de cache no hace ``.decode()``.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.core.redis import get_redis
from app.database import db_manager
from app.models.feature_flag import FeatureFlag
from app.repositories.feature_flag_repository import FeatureFlagRepository

logger = logging.getLogger("app.services.feature_flag")

CACHE_TTL_SECONDS = 60
CACHE_PREFIX = "feature_flag:"


class FeatureFlagService:
    """Lee flags de feature con cache en Redis."""

    @staticmethod
    async def is_enabled(key: str, default: bool = False) -> bool:
        """Devuelve si una flag está activa (Redis L1 → DB fallback → write-back)."""
        cache_key = f"{CACHE_PREFIX}{key}"
        redis = get_redis()

        if redis is not None:
            try:
                cached = await redis.get(cache_key)
                if cached is not None:
                    return cached == "1"
            except Exception as exc:  # noqa: BLE001 — fail-soft caching
                logger.warning("Redis feature_flag read failed: %s", exc)

        async with db_manager.get_session() as session:
            repo = FeatureFlagRepository(session)
            flag = await repo.get_by_key(key)
            value = flag.value if flag is not None else default

        if redis is not None:
            try:
                await redis.setex(cache_key, CACHE_TTL_SECONDS, "1" if value else "0")
            except Exception as exc:  # noqa: BLE001 — fail-soft caching
                logger.warning("Redis feature_flag write failed: %s", exc)

        return value

    @staticmethod
    async def invalidate_cache(key: str) -> None:
        redis = get_redis()
        if redis is not None:
            try:
                await redis.delete(f"{CACHE_PREFIX}{key}")
            except Exception as exc:  # noqa: BLE001 — fail-soft caching
                logger.warning("Redis feature_flag invalidate failed: %s", exc)

    @staticmethod
    async def set_flag(
        key: str, value: bool, description: str | None = None
    ) -> FeatureFlag:
        """Crea o actualiza una flag (uso admin). Invalida la cache."""
        async with db_manager.get_session() as session:
            repo = FeatureFlagRepository(session)
            flag = await repo.get_by_key(key)
            if flag is None:
                flag = FeatureFlag(key=key, value=value, description=description)
                await repo.create(flag)
            else:
                flag.value = value
                if description is not None:
                    flag.description = description
                flag.updated_at = datetime.now(UTC)
                await repo.update(flag)

        await FeatureFlagService.invalidate_cache(key)
        return flag

    @staticmethod
    async def delete_flag(key: str) -> bool:
        """Elimina una flag. Devuelve True si existía."""
        async with db_manager.get_session() as session:
            repo = FeatureFlagRepository(session)
            flag = await repo.get_by_key(key)
            if flag is None:
                return False
            await repo.delete(flag)

        await FeatureFlagService.invalidate_cache(key)
        return True

    @staticmethod
    async def list_flags() -> list[FeatureFlag]:
        async with db_manager.get_session() as session:
            repo = FeatureFlagRepository(session)
            return await repo.list_all()


async def flag_enabled(key: str, default: bool = False) -> bool:
    """Alias de conveniencia para el resto de módulos."""
    return await FeatureFlagService.is_enabled(key, default)