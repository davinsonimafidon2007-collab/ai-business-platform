"""Async Redis client for shared caching and distributed rate limiting.

Fails soft in development/test: if Redis is unavailable, get/set become no-ops
and the app continues using in-memory fallbacks. In production the app refuses
to start if Redis is unreachable.
"""

from __future__ import annotations

import logging

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: redis.Redis | None = None


async def init_redis() -> None:
    """Create the shared connection pool. Call from app lifespan."""
    global _client
    if _client is not None:
        return
    try:
        _client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=2.0,
            socket_timeout=2.0,
        )
        await _client.ping()
        logger.info("Redis connected: %s", settings.redis_url)
    except Exception as exc:
        if settings.environment == "production":
            raise RuntimeError(
                "Redis is required in production but could not be reached: "
                f"{exc}"
            ) from exc
        logger.warning(
            "Redis unavailable (%s) — cache and rate-limit fall back to "
            "in-memory mode",
            exc,
        )
        _client = None


async def close_redis() -> None:
    """Close the shared client. Call from app lifespan shutdown."""
    global _client
    if _client is not None:
        try:
            await _client.aclose()
        except redis.RedisError:
            logger.exception("Error closing Redis")
        _client = None


def get_redis() -> redis.Redis | None:
    """Return the live client or None if Redis is down / not initialized."""
    return _client


async def cache_get(key: str) -> str | None:
    client = get_redis()
    if client is None:
        return None
    try:
        return await client.get(key)
    except redis.RedisError:
        logger.warning("Redis GET failed for key=%s", key, exc_info=True)
        return None


async def cache_set(key: str, value: str, ttl_seconds: int) -> None:
    client = get_redis()
    if client is None:
        return
    try:
        await client.set(key, value, ex=max(1, int(ttl_seconds)))
    except redis.RedisError:
        logger.warning("Redis SET failed for key=%s", key, exc_info=True)


async def cache_delete(key: str) -> None:
    client = get_redis()
    if client is None:
        return
    try:
        await client.delete(key)
    except redis.RedisError:
        logger.warning("Redis DELETE failed for key=%s", key, exc_info=True)


def market_cache_key(market_hash: str) -> str:
    """Stable key for market estimation cache entries."""
    return f"market:est:{market_hash}"


async def rate_limit_hit(key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
    """Incrementa un contador atómico en Redis para rate limiting distribuido.

    Returns (allowed, retry_after_seconds):
        allowed=True  → dentro del límite
        allowed=False → superó el límite; retry_after ≈ segundos hasta fin de ventana

    Raises RuntimeError si Redis no está disponible (o si falla la operación),
    para que el caller pueda hacer fallback a la memoria local.
    """
    client = get_redis()
    if client is None:
        raise RuntimeError("redis unavailable")

    try:
        # INCR + TTL en una sola operación atómica (pipeline)
        pipe = client.pipeline()
        pipe.incr(key)
        pipe.ttl(key)
        count, ttl = await pipe.execute()
        count = int(count)
        ttl = int(ttl)

        # Clave sin TTL (primer incremento de la ventana): fijar la ventana
        if ttl < 0:
            await client.expire(key, max(1, int(window_seconds)))
            ttl = int(window_seconds)

        if count > limit:
            return False, max(1, ttl)
        return True, 0
    except redis.RedisError:
        logger.warning("Redis rate_limit_hit failed for key=%s", key, exc_info=True)
        raise
