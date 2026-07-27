from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response

from app.exceptions import AuthenticationError
from app.middleware.authentication_middleware import AuthenticationMiddleware


@pytest.fixture
def app() -> FastAPI:
    return FastAPI()


@pytest.fixture
def middleware(app: FastAPI) -> AuthenticationMiddleware:
    return AuthenticationMiddleware(app)


@pytest.mark.asyncio
async def test_public_paths_skip_authentication(middleware: AuthenticationMiddleware) -> None:
    """Test that public paths are not authenticated."""
    request = MagicMock(spec=Request)
    request.url.path = "/health"
    request.headers = {}

    call_next = AsyncMock(return_value=Response())

    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 200
    call_next.assert_called_once()


@pytest.mark.asyncio
async def test_auth_paths_skip_authentication(middleware: AuthenticationMiddleware) -> None:
    """Test that auth paths are not authenticated."""
    request = MagicMock(spec=Request)
    request.url.path = "/auth/login"
    request.headers = {}

    call_next = AsyncMock(return_value=Response())

    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 200
    call_next.assert_called_once()


@pytest.mark.asyncio
async def test_no_auth_header_passes_through(middleware: AuthenticationMiddleware) -> None:
    """Test that requests without auth headers pass through."""
    request = MagicMock(spec=Request)
    request.url.path = "/api/v1/search"
    request.headers = {}
    request.state = MagicMock()

    call_next = AsyncMock(return_value=Response())

    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 200
    call_next.assert_called_once()


@pytest.mark.asyncio
async def test_invalid_jwt_returns_401(middleware: AuthenticationMiddleware) -> None:
    """Test that invalid JWT returns 401."""
    request = MagicMock(spec=Request)
    request.url.path = "/api/v1/search"
    request.headers = {"Authorization": "Bearer invalid_token"}
    request.state = MagicMock()

    call_next = AsyncMock(return_value=Response())

    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 401
    call_next.assert_not_called()


@pytest.mark.asyncio
async def test_invalid_api_key_returns_401(middleware: AuthenticationMiddleware) -> None:
    """Test that invalid API key returns 401."""
    request = MagicMock(spec=Request)
    request.url.path = "/api/v1/search"
    request.headers = {"X-API-Key": "invalid_key"}
    request.state = MagicMock()

    call_next = AsyncMock(return_value=Response())

    with patch.object(middleware, "_authenticate_api_key", new=AsyncMock(side_effect=AuthenticationError("Invalid API key"))):
        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 401
        call_next.assert_not_called()


@pytest.mark.asyncio
async def test_valid_jwt_sets_user_in_state(middleware: AuthenticationMiddleware) -> None:
    """Test that valid JWT sets user in request state."""
    request = MagicMock(spec=Request)
    request.url.path = "/api/v1/search"
    request.headers = {"Authorization": "Bearer valid_token"}
    request.state = MagicMock()

    call_next = AsyncMock(return_value=Response())

    with patch.object(middleware, "_authenticate_jwt", new=AsyncMock(return_value=MagicMock(id="user-1"))):
        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200
        assert request.state.auth_method == "jwt"
        call_next.assert_called_once()


@pytest.mark.asyncio
async def test_valid_api_key_sets_user_in_state(middleware: AuthenticationMiddleware) -> None:
    """Test that valid API key sets user in request state."""
    request = MagicMock(spec=Request)
    request.url.path = "/api/v1/search"
    request.headers = {"X-API-Key": "abp_live_valid_key"}
    request.state = MagicMock()

    call_next = AsyncMock(return_value=Response())

    with patch.object(middleware, "_authenticate_api_key", new=AsyncMock(return_value=MagicMock(id="user-1"))):
        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200
        assert request.state.auth_method == "api_key"
        call_next.assert_called_once()
