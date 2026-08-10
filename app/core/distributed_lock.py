"""Distributed lock via Redis for multi-instance job safety.

Provides a simple ``RedisLock`` context manager that uses Redis ``SET NX EX``
for atomic lock acquisition. Falls back to always-acquire (no-op) when Redis
is unavailable, so jobs still run in single-instance mode without Redis.

Usage::

    async with RedisLock("refresh_market_cache", ttl=300):
        await do_expensive_work()
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from app.core.redis import get_redis

logger = logging.getLogger(__name__)


class RedisLock:
    """Async context manager for a Redis-based distributed lock.

    Args:
        name: Lock key name (e.g. job name).
        ttl: Lock expiry in seconds (default 300s = 5 min).
        blocking: If False, raise ``LockError`` immediately when lock is held.
    """

    def __init__(
        self,
        name: str,
        ttl: int = 300,
        blocking: bool = True,
    ) -> None:
        self._key = f"lock:job:{name}"
        self._ttl = ttl
        self._blocking = blocking
        self._token: str | None = None

    async def __aenter__(self) -> RedisLock:
        client = get_redis()
        if client is None:
            # No Redis → single instance, always acquire
            return self

        self._token = f"{time.monotonic_ns()}"
        acquired = False
        try:
            acquired = bool(
                await client.set(self._key, self._token, nx=True, ex=self._ttl)
            )
        except Exception:
            logger.warning("RedisLock: failed to acquire %s", self._key, exc_info=True)

        if not acquired and self._blocking:
            # Simple spin-retry with backoff (max 10s)
            for _ in range(20):
                await asyncio.sleep(0.5)
                try:
                    acquired = bool(
                        await client.set(
                            self._key, self._token, nx=True, ex=self._ttl
                        )
                    )
                except Exception:
                    break
                if acquired:
                    break

        if not acquired and not self._blocking:
            raise LockError(f"Lock {self._key} is held by another instance")

        return self

    async def __aexit__(self, *args: Any) -> None:
        client = get_redis()
        if client is None or self._token is None:
            return
        try:
            # Only release if we own it (Lua CAS)
            await client.eval(
                """
                if redis.call("get", KEYS[1]) == ARGV[1] then
                    return redis.call("del", KEYS[1])
                else
                    return 0
                end
                """,
                1,
                self._key,
                self._token,
            )
        except Exception:
            logger.warning("RedisLock: failed to release %s", self._key, exc_info=True)


class LockError(Exception):
    """Raised when a non-blocking lock acquisition fails."""
