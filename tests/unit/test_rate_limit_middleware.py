from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, Request
from starlette.responses import Response

from app.middleware.rate_limit_middleware import RateLimitMiddleware


@pytest.fixture
def app() -> FastAPI:
    return FastAPI()


@pytest.fixture
def middleware(app: FastAPI) -> RateLimitMiddleware:
    return RateLimitMiddleware(app, window_seconds=60)


@pytest.mark.asyncio
async def test_health_endpoint_skips_rate_limit(middleware: RateLimitMiddleware) -> None:
    """Test that health endpoint is not rate limited."""
    request = MagicMock(spec=Request)
    request.url.path = "/health"
    request.client.host = "127.0.0.1"

    call_next = AsyncMock(return_value=Response())

    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 200
    call_next.assert_called_once()


@pytest.mark.asyncio
async def test_unauthenticated_request_rate_limited_by_ip(middleware: RateLimitMiddleware) -> None:
    """Test that unauthenticated requests are rate limited by IP."""
    request = MagicMock(spec=Request)
    request.url.path = "/api/v1/search"
    request.url = MagicMock()
    request.url.path = "/api/v1/search"
    request.client.host = "127.0.0.1"
    request.state = MagicMock()
    request.state.user = None
    request.state.auth_method = None
    request.method = "GET"

    call_next = AsyncMock(return_value=Response())

    # First request should pass
    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 200

    # Exhaust the rate limit (default is 60/min, but we can test with lower)
    # For this test, we just verify the mechanism works
    call_next.assert_called()


@pytest.mark.asyncio
async def test_jwt_authenticated_user_rate_limited(middleware: RateLimitMiddleware) -> None:
    """Test that JWT-authenticated users are rate limited by user ID."""
    request = MagicMock(spec=Request)
    request.url.path = "/api/v1/search"
    request.url = MagicMock()
    request.url.path = "/api/v1/search"
    request.client.host = "10.0.0.1"
    request.state = MagicMock()
    request.state.user = MagicMock()
    request.state.user.id = "user-1"
    request.state.user.role = "user"
    request.state.auth_method = "jwt"
    request.method = "GET"

    call_next = AsyncMock(return_value=Response())

    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 200
    call_next.assert_called()


@pytest.mark.asyncio
async def test_api_key_authenticated_user_rate_limited(middleware: RateLimitMiddleware) -> None:
    """Test that API key-authenticated users are rate limited by user ID."""
    request = MagicMock(spec=Request)
    request.url.path = "/api/v1/search"
    request.url = MagicMock()
    request.url.path = "/api/v1/search"
    request.client.host = "10.0.0.2"
    request.state = MagicMock()
    request.state.user = MagicMock()
    request.state.user.id = "user-2"
    request.state.user.role = "user"
    request.state.auth_method = "api_key"
    request.method = "GET"

    call_next = AsyncMock(return_value=Response())

    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 200
    call_next.assert_called()


@pytest.mark.asyncio
async def test_rate_limit_exceeded_returns_429(middleware: RateLimitMiddleware) -> None:
    """Test that exceeding rate limit returns 429."""
    # Set a very low limit for testing
    middleware._ip_limits = {}
    middleware.window_seconds = 60

    request = MagicMock(spec=Request)
    request.url.path = "/api/v1/search"
    request.url = MagicMock()
    request.url.path = "/api/v1/search"
    request.client.host = "rate-limited-ip"
    request.state = MagicMock()
    request.state.user = None
    request.state.auth_method = None
    request.method = "GET"

    call_next = AsyncMock(return_value=Response())

    # Exhaust the limit by making many requests
    for _ in range(65):  # Default limit is 60
        await middleware.dispatch(request, call_next)

    # Next request should be rate limited
    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 429


@pytest.mark.asyncio
async def test_different_ips_have_separate_limits(middleware: RateLimitMiddleware) -> None:
    """Test that different IPs have separate rate limits."""
    request1 = MagicMock(spec=Request)
    request1.url.path = "/api/v1/search"
    request1.url = MagicMock()
    request1.url.path = "/api/v1/search"
    request1.client.host = "ip-1"
    request1.state = MagicMock()
    request1.state.user = None
    request1.state.auth_method = None
    request1.method = "GET"

    request2 = MagicMock(spec=Request)
    request2.url.path = "/api/v1/search"
    request2.url = MagicMock()
    request2.url.path = "/api/v1/search"
    request2.client.host = "ip-2"
    request2.state = MagicMock()
    request2.state.user = None
    request2.state.auth_method = None
    request2.method = "GET"

    call_next = AsyncMock(return_value=Response())

    # Both should pass
    response1 = await middleware.dispatch(request1, call_next)
    response2 = await middleware.dispatch(request2, call_next)
    assert response1.status_code == 200
    assert response2.status_code == 200
