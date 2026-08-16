"""COV.GATE.1: caminos de app/dependencies/auth.py no cubiertos.

El gate de cobertura destapó que solo se ejercitaba el bypass de
``auth_disabled``. Aquí se cubre el camino JWT real y las denegaciones de
rol/permiso, que son precisamente la lógica de seguridad.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import settings
from app.dependencies.auth import (
    get_current_user,
    require_permission,
    require_role,
)
from app.exceptions import (
    AuthenticationError,
    AuthorizationError,
    UserNotFoundError,
)
from app.models.role import Role
from app.models.user import User


class _FakeRequest:
    def __init__(self, user: object | None = None) -> None:
        self.state = SimpleNamespace(user=user)


def _user(role: Role = Role.USER, is_active: bool = True) -> User:
    return User(
        id="11111111-1111-1111-1111-111111111111",
        email="user@example.com",
        hashed_password="x",
        full_name="Test User",
        is_active=is_active,
        is_verified=True,
        role=role,
    )


def _credentials(token: str = "tok") -> MagicMock:
    creds = MagicMock()
    creds.credentials = token
    return creds


@pytest.fixture(autouse=True)
def _auth_enabled(monkeypatch: pytest.MonkeyPatch):
    """Estos tests cubren el camino JWT, no el bypass personal."""
    monkeypatch.setattr(settings, "auth_disabled", False)


@pytest.mark.asyncio
async def test_middleware_user_short_circuits_jwt() -> None:
    """Si el middleware ya autenticó, no se vuelve a decodificar el token."""
    existing = _user()

    with patch("app.dependencies.auth.AuthService") as auth_service_cls:
        result = await get_current_user(
            _FakeRequest(user=existing), credentials=None, session=None
        )

    assert result is existing
    auth_service_cls.assert_not_called()


@pytest.mark.asyncio
async def test_valid_jwt_returns_user() -> None:
    expected = _user()

    auth_service_cls = MagicMock()
    auth_service_cls.return_value.decode_access_token.return_value = {
        "sub": str(expected.id)
    }
    user_service_cls = MagicMock()
    user_service_cls.return_value.get_user = AsyncMock(return_value=expected)

    with (
        patch("app.dependencies.auth.AuthService", auth_service_cls),
        patch("app.dependencies.auth.UserService", user_service_cls),
        patch("app.dependencies.auth.UserRepository", MagicMock()),
    ):
        result = await get_current_user(
            _FakeRequest(), credentials=_credentials(), session=None
        )

    assert result is expected


@pytest.mark.asyncio
async def test_token_without_sub_is_rejected() -> None:
    auth_service_cls = MagicMock()
    auth_service_cls.return_value.decode_access_token.return_value = {}

    with (
        patch("app.dependencies.auth.AuthService", auth_service_cls),
        patch("app.dependencies.auth.UserRepository", MagicMock()),
    ):
        with pytest.raises(AuthenticationError, match="Invalid token"):
            await get_current_user(
                _FakeRequest(), credentials=_credentials(), session=None
            )


@pytest.mark.asyncio
async def test_inactive_user_is_rejected() -> None:
    inactive = _user(is_active=False)

    auth_service_cls = MagicMock()
    auth_service_cls.return_value.decode_access_token.return_value = {
        "sub": str(inactive.id)
    }
    user_service_cls = MagicMock()
    user_service_cls.return_value.get_user = AsyncMock(return_value=inactive)

    with (
        patch("app.dependencies.auth.AuthService", auth_service_cls),
        patch("app.dependencies.auth.UserService", user_service_cls),
        patch("app.dependencies.auth.UserRepository", MagicMock()),
    ):
        with pytest.raises(AuthenticationError, match="inactive"):
            await get_current_user(
                _FakeRequest(), credentials=_credentials(), session=None
            )


@pytest.mark.asyncio
async def test_unknown_user_maps_to_authentication_error() -> None:
    """Un `sub` que ya no existe no debe filtrar UserNotFoundError."""
    auth_service_cls = MagicMock()
    auth_service_cls.return_value.decode_access_token.return_value = {"sub": "ghost"}
    user_service_cls = MagicMock()
    user_service_cls.return_value.get_user = AsyncMock(
        side_effect=UserNotFoundError("nope")
    )

    with (
        patch("app.dependencies.auth.AuthService", auth_service_cls),
        patch("app.dependencies.auth.UserService", user_service_cls),
        patch("app.dependencies.auth.UserRepository", MagicMock()),
    ):
        with pytest.raises(AuthenticationError, match="Invalid token"):
            await get_current_user(
                _FakeRequest(), credentials=_credentials(), session=None
            )


@pytest.mark.asyncio
async def test_require_role_allows_and_denies() -> None:
    dependency = require_role(Role.ADMIN)

    admin = _user(role=Role.ADMIN)
    assert await dependency(current_user=admin) is admin

    with pytest.raises(AuthorizationError, match="Insufficient permissions"):
        await dependency(current_user=_user(role=Role.USER))


@pytest.mark.asyncio
async def test_require_permission_allows_and_denies() -> None:
    dependency = require_permission("search")
    admin = _user(role=Role.ADMIN)

    with patch("app.dependencies.auth.permission_service") as perms:
        perms.can.return_value = True
        assert await dependency(current_user=admin) is admin

        perms.can.return_value = False
        with pytest.raises(AuthorizationError, match="Insufficient permissions"):
            await dependency(current_user=admin)
