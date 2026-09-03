"""AuthenticationMiddleware — tests de COMPORTAMIENTO real (TEST.C fix).

La versión anterior mockeaba los propios métodos ``_authenticate_jwt`` /
``_authenticate_api_key`` del middleware bajo test: la lógica de auth real
nunca llegaba a ejecutarse, así que un bug de parsing JWT habría pasado en
verde. Ahora el middleware corre contra SQLite en memoria (mismo patrón que
``tests/integration/database/conftest.py``) con usuario y API key REALES, y
los JWT se firman con ``app.core.auth.create_access_token``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi import Request
from pwdlib import PasswordHash
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.core.auth import create_access_token
from app.core.config import settings
from app.database.manager import DatabaseManager
from app.middleware import authentication_middleware as auth_mw_module
from app.middleware.authentication_middleware import AuthenticationMiddleware
from app.models.api_key import ApiKey
from app.models.base import Base
from app.models.user import User

password_hasher = PasswordHash.recommended()

USER_ID = "22222222-2222-4222-8222-222222222222"
VALID_API_KEY = "abp_live_testkey_0123456789abcdef0123456789abcdef"


@pytest.fixture(autouse=True)
def _auth_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fuerza auth ON: este middleware solo actúa fuera del modo personal."""
    monkeypatch.setattr(auth_mw_module.settings, "auth_disabled", False)


@pytest_asyncio.fixture
async def db_manager(monkeypatch: pytest.MonkeyPatch) -> AsyncSession:
    manager = DatabaseManager("sqlite+aiosqlite://", echo=False)
    async with manager._engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with manager.get_session() as session:
        user = User(id=USER_ID, email="middleware@example.com", hashed_password="x")
        session.add(user)
        session.add(
            ApiKey(
                user_id=USER_ID,
                name="middleware-test-key",
                key_hash=password_hasher.hash(VALID_API_KEY),
                # generate_api_key() almacena el prefijo CON guion bajo final
                prefix=f"{settings.api_key_prefix}_",
                is_active=True,
            )
        )
        await session.commit()

    # El middleware construye sus servicios sobre el db_manager global:
    # lo sustituimos por el manager SQLite real (misma interfaz).
    monkeypatch.setattr(auth_mw_module, "db_manager", manager)
    yield manager  # type: ignore[misc]
    await manager.shutdown()


@pytest.fixture
def middleware() -> AuthenticationMiddleware:
    return AuthenticationMiddleware(app=SimpleNamespace())


def _request(
    path: str = "/api/v1/dashboard/stats",
    headers: dict[str, str] | None = None,
) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": [
            (k.lower().encode(), v.encode()) for k, v in (headers or {}).items()
        ],
        "cookies": {},
        "query_string": b"",
    }
    request = Request(scope)
    return request


@pytest.mark.asyncio
async def test_public_paths_skip_authentication(middleware: AuthenticationMiddleware) -> None:
    call_next = AsyncMock(return_value=Response())
    response = await middleware.dispatch(_request("/health"), call_next)
    assert response.status_code == 200
    call_next.assert_called_once()


@pytest.mark.asyncio
async def test_auth_paths_skip_authentication(middleware: AuthenticationMiddleware) -> None:
    call_next = AsyncMock(return_value=Response())
    response = await middleware.dispatch(_request("/api/v1/auth/login"), call_next)
    assert response.status_code == 200
    call_next.assert_called_once()


@pytest.mark.asyncio
async def test_no_auth_header_passes_through(db_manager, middleware: AuthenticationMiddleware) -> None:
    call_next = AsyncMock(return_value=Response())
    request = _request()
    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 200
    call_next.assert_called_once()
    assert not hasattr(request.state, "user")


@pytest.mark.asyncio
async def test_invalid_jwt_returns_401(db_manager, middleware: AuthenticationMiddleware) -> None:
    call_next = AsyncMock(return_value=Response())
    request = _request(headers={"Authorization": "Bearer no-es-un-jwt"})
    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 401
    assert response.body == b'{"detail":"Invalid or expired token"}'
    call_next.assert_not_called()


@pytest.mark.asyncio
async def test_valid_jwt_sets_user_in_state(db_manager, middleware: AuthenticationMiddleware) -> None:
    token = create_access_token({"sub": USER_ID})
    call_next = AsyncMock(return_value=Response())
    request = _request(headers={"Authorization": f"Bearer {token}"})
    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 200
    assert str(request.state.user.id) == USER_ID
    assert request.state.auth_method == "jwt"
    call_next.assert_called_once()


@pytest.mark.asyncio
async def test_jwt_of_unknown_user_returns_401(db_manager, middleware: AuthenticationMiddleware) -> None:
    token = create_access_token({"sub": "99999999-9999-4999-8999-999999999999"})
    call_next = AsyncMock(return_value=Response())
    response = await middleware.dispatch(
        _request(headers={"Authorization": f"Bearer {token}"}), call_next
    )
    assert response.status_code == 401
    call_next.assert_not_called()


@pytest.mark.asyncio
async def test_invalid_api_key_returns_401(db_manager, middleware: AuthenticationMiddleware) -> None:
    call_next = AsyncMock(return_value=Response())
    response = await middleware.dispatch(
        _request(headers={"X-API-Key": "abp_live_totally_invalid"}), call_next
    )
    assert response.status_code == 401
    call_next.assert_not_called()


@pytest.mark.asyncio
async def test_valid_api_key_sets_user_in_state(db_manager, middleware: AuthenticationMiddleware) -> None:
    call_next = AsyncMock(return_value=Response())
    request = _request(headers={"X-API-Key": VALID_API_KEY})
    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 200
    assert str(request.state.user.id) == USER_ID
    assert request.state.auth_method == "api_key"
    call_next.assert_called_once()


@pytest.mark.asyncio
async def test_expired_api_key_returns_401(db_manager, middleware: AuthenticationMiddleware) -> None:
    manager: DatabaseManager = db_manager
    expired = ApiKey(
        user_id=USER_ID,
        name="middleware-expired-key",
        key_hash=password_hasher.hash("abp_live_expired_0123456789abcdef"),
        prefix=f"{settings.api_key_prefix}_",
        is_active=True,
        expires_at=datetime.now(UTC).replace(year=2020),
    )
    async with manager.get_session() as session:
        session.add(expired)
        await session.commit()

    call_next = AsyncMock(return_value=Response())
    response = await middleware.dispatch(
        _request(headers={"X-API-Key": "abp_live_expired_0123456789abcdef"}),
        call_next,
    )
    assert response.status_code == 401
    call_next.assert_not_called()
