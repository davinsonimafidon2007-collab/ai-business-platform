from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.middleware.rate_limit_middleware import RateLimitMiddleware


@pytest.mark.asyncio
async def test_rate_limit_hit_denies_over_limit() -> None:
    """count > limit → allowed=False y retry_after ≈ ttl restante."""
    from app.core import redis as redis_mod

    fake = AsyncMock()
    pipe = MagicMock()
    pipe.execute = AsyncMock(return_value=[6, 50])
    fake.pipeline = lambda: pipe

    with patch.object(redis_mod, "get_redis", return_value=fake):
        allowed, retry_after = await redis_mod.rate_limit_hit(
            "rl:test", limit=5, window_seconds=60
        )

    assert allowed is False
    assert retry_after == 50


@pytest.mark.asyncio
async def test_rate_limit_hit_allows_under_limit() -> None:
    """count <= limit → allowed=True y retry_after=0."""
    from app.core import redis as redis_mod

    fake = AsyncMock()
    pipe = MagicMock()
    pipe.execute = AsyncMock(return_value=[2, 40])
    fake.pipeline = lambda: pipe
    fake.expire = AsyncMock()

    with patch.object(redis_mod, "get_redis", return_value=fake):
        allowed, retry_after = await redis_mod.rate_limit_hit(
            "rl:test", limit=5, window_seconds=60
        )

    assert allowed is True
    assert retry_after == 0


@pytest.mark.asyncio
async def test_rate_limit_hit_raises_when_redis_unavailable() -> None:
    """get_redis() → None ⇒ RuntimeError (el middleware hace fallback local)."""
    from app.core import redis as redis_mod

    with patch.object(redis_mod, "get_redis", return_value=None):
        with pytest.raises(RuntimeError):
            await redis_mod.rate_limit_hit("rl:test", limit=5, window_seconds=60)


@pytest.mark.asyncio
async def test_rate_limit_hit_sets_expire_on_first_hit() -> None:
    """TTL < 0 (primer incremento) ⇒ se fija EXPIRE con la ventana."""
    from app.core import redis as redis_mod

    fake = AsyncMock()
    pipe = MagicMock()
    pipe.execute = AsyncMock(return_value=[1, -1])
    fake.pipeline = lambda: pipe
    fake.expire = AsyncMock()

    with patch.object(redis_mod, "get_redis", return_value=fake):
        allowed, retry_after = await redis_mod.rate_limit_hit(
            "rl:test", limit=5, window_seconds=60
        )

    fake.expire.assert_awaited_once_with("rl:test", 60)
    assert allowed is True
    assert retry_after == 0


@pytest.mark.asyncio
async def test_allow_falls_back_to_local_when_redis_unavailable() -> None:
    """Sin Redis, _allow usa la memoria local (mismo comportamiento previo)."""
    from app.core import redis as redis_mod

    app = object()
    middleware = RateLimitMiddleware(app, window_seconds=60)

    with patch.object(redis_mod, "get_redis", return_value=None):
        # Límite 1: primera petición OK, segunda denegada
        ok1 = await middleware._allow(
            "rl:ip:1.2.3.4",
            1,
            60,
            local_bucket=middleware._ip_limits,
            local_key="1.2.3.4",
        )
        ok2 = await middleware._allow(
            "rl:ip:1.2.3.4",
            1,
            60,
            local_bucket=middleware._ip_limits,
            local_key="1.2.3.4",
        )

    assert ok1 is True
    assert ok2 is False


@pytest.mark.asyncio
async def test_allow_uses_redis_when_available() -> None:
    """Con Redis disponible, _allow usa rate_limit_hit y respeta el resultado."""
    from app.core import redis as redis_mod
    from app.middleware import rate_limit_middleware as mw_mod

    app = object()
    middleware = RateLimitMiddleware(app, window_seconds=60)

    fake = AsyncMock()
    pipe = MagicMock()
    pipe.execute = AsyncMock(return_value=[6, 50])
    fake.pipeline = lambda: pipe

    # rate_limit_hit usa get_redis() de app.core.redis; _allow usa el importado
    # en rate_limit_middleware. Hay que parchear ambos para simular Redis 'up'.
    with patch.object(redis_mod, "get_redis", return_value=fake), patch.object(
        mw_mod, "get_redis", return_value=fake
    ):
        allowed = await middleware._allow(
            "rl:ep:GET:/api/v1/search:1.2.3.4",
            5,
            60,
            local_bucket=middleware._endpoint_limits,
            local_key="GET:/api/v1/search",
        )

    assert allowed is False
