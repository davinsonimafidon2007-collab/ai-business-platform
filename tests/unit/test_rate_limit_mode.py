"""Tests for PERF-001 rate-limit mode visibility.

Covers:
- X-RateLimit-Mode header on allowed (200) and rejected (429) responses.
- Redis-up → header ``redis``.
- Redis-down → header ``memory``.
- Production Redis-down → visible logger.error (not silent), throttled.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request
from starlette.responses import Response

from app.middleware import rate_limit_middleware as mw_mod
from app.middleware.rate_limit_middleware import (
    RATE_LIMIT_MODE_HEADER,
    RateLimitMiddleware,
)


@pytest.fixture(autouse=True)
def _reset_fallback_throttle():
    """The fallback ERROR log is throttled to ~1/10s; reset between tests."""
    mw_mod._FALLBACK_LOG_THROTTLE.reset()
    yield
    mw_mod._FALLBACK_LOG_THROTTLE.reset()


def _unauth_request(path: str, ip: str) -> Request:
    request = MagicMock(spec=Request)
    request.url.path = path
    request.client.host = ip
    request.state.user = None
    request.state.auth_method = None
    request.method = "GET"
    return request


@pytest.mark.asyncio
async def test_allowed_response_memory_mode_header() -> None:
    """Sin Redis → la respuesta lleva X-RateLimit-Mode: memory."""
    mw = RateLimitMiddleware(object(), window_seconds=60)
    request = _unauth_request("/api/v1/search", "ip-memory")

    with patch.object(mw_mod, "get_redis", return_value=None):
        response = await mw.dispatch(request, AsyncMock(return_value=Response()))

    assert response.status_code == 200
    assert response.headers.get(RATE_LIMIT_MODE_HEADER) == "memory"


@pytest.mark.asyncio
async def test_allowed_response_redis_mode_header() -> None:
    """Con Redis up → la respuesta lleva X-RateLimit-Mode: redis."""
    from app.core import redis as redis_mod

    mw = RateLimitMiddleware(object(), window_seconds=60)
    fake = AsyncMock()
    pipe = AsyncMock()
    pipe.execute = AsyncMock(return_value=[1, 55])
    fake.pipeline = lambda: pipe
    fake.expire = AsyncMock()

    request = _unauth_request("/api/v1/search", "ip-redis")
    with patch.object(redis_mod, "get_redis", return_value=fake), patch.object(
        mw_mod, "get_redis", return_value=fake
    ):
        response = await mw.dispatch(request, AsyncMock(return_value=Response()))

    assert response.status_code == 200
    assert response.headers.get(RATE_LIMIT_MODE_HEADER) == "redis"


def test_too_many_response_has_mode_header() -> None:
    """El 429 también expone el modo (memory en este caso)."""
    mw = RateLimitMiddleware(object(), window_seconds=60)
    mw._mode = "memory"

    response = mw._too_many(60)

    assert response.status_code == 429
    assert response.headers.get("Retry-After") == "60"
    assert response.headers.get(RATE_LIMIT_MODE_HEADER) == "memory"


@pytest.mark.asyncio
async def test_production_fallback_logs_error(monkeypatch) -> None:
    """Production + Redis down → se llama a logger.error (fallback visible)."""
    from app.core import redis as redis_mod

    mw = RateLimitMiddleware(object(), window_seconds=60)
    monkeypatch.setattr(mw_mod.settings, "environment", "production")

    with patch.object(redis_mod, "get_redis", return_value=None), patch.object(
        mw_mod, "get_redis", return_value=None
    ), patch.object(mw_mod, "logger") as mock_logger:
        allowed = await mw._allow(
            "rl:test", 5, 60, local_bucket=mw._ip_limits, local_key="1.2.3.4"
        )

    assert allowed is True
    mock_logger.error.assert_called_once()


@pytest.mark.asyncio
async def test_development_fallback_logs_debug_not_error(monkeypatch) -> None:
    """Development + Redis down → solo debug (no error)."""
    from app.core import redis as redis_mod

    mw = RateLimitMiddleware(object(), window_seconds=60)
    monkeypatch.setattr(mw_mod.settings, "environment", "development")

    with patch.object(redis_mod, "get_redis", return_value=None), patch.object(
        mw_mod, "get_redis", return_value=None
    ), patch.object(mw_mod, "logger") as mock_logger:
        allowed = await mw._allow(
            "rl:test", 5, 60, local_bucket=mw._ip_limits, local_key="1.2.3.4"
        )

    assert allowed is True
    mock_logger.error.assert_not_called()
    mock_logger.debug.assert_called_once()


@pytest.mark.asyncio
async def test_redis_failure_at_runtime_falls_back_and_logs(monkeypatch) -> None:
    """Redis 'up' pero rate_limit_hit lanza → fallback memory + header memory."""
    from app.core import redis as redis_mod

    mw = RateLimitMiddleware(object(), window_seconds=60)
    monkeypatch.setattr(mw_mod.settings, "environment", "production")

    broken_client = MagicMock()
    # pipeline().execute() lanza → rate_limit_hit levanta RuntimeError
    broken_client.pipeline.return_value.execute.side_effect = RuntimeError("boom")

    request = _unauth_request("/api/v1/search", "ip-broken")
    with patch.object(redis_mod, "get_redis", return_value=broken_client), patch.object(
        mw_mod, "get_redis", return_value=broken_client
    ), patch.object(mw_mod, "logger") as mock_logger:
        response = await mw.dispatch(request, AsyncMock(return_value=Response()))

    assert response.status_code == 200
    assert response.headers.get(RATE_LIMIT_MODE_HEADER) == "memory"
    mock_logger.error.assert_called_once()
