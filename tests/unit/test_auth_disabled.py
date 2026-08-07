"""PERSONAL.NOAUTH: flag AUTH_DISABLED off/on en get_current_user.

- Flag ON  → get_current_user devuelve el usuario local ADMIN sin mirar Bearer.
- Flag OFF → sigue exigiendo JWT (no debe romperse la auth actual).
- PersonalUserService.ensure_local_user  → get-or-create de la fila en users.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import settings
from app.core.local_user import LOCAL_USER_EMAIL, LOCAL_USER_ID_STR
from app.dependencies.auth import get_current_user
from app.exceptions import AuthenticationError
from app.models.role import Role
from app.models.user import User
from app.services.personal_user_service import PersonalUserService


class _FakeRequest:
    def __init__(self, user: object | None = None) -> None:
        self.state = SimpleNamespace(user=user)


def _local_admin() -> User:
    return User(
        id=LOCAL_USER_ID_STR,
        email=LOCAL_USER_EMAIL,
        hashed_password="",
        full_name="Local Admin",
        is_active=True,
        is_verified=True,
        role=Role.ADMIN,
    )


@pytest.mark.asyncio
async def test_auth_disabled_skips_jwt_and_returns_local_admin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Flag ON: sin header Authorization → usuario local ADMIN, sin decodificar JWT."""
    monkeypatch.setattr(settings, "auth_disabled", True)

    local_user = _local_admin()
    fake_service_cls = MagicMock()
    fake_instance = fake_service_cls.return_value
    fake_instance.ensure_local_user = AsyncMock(return_value=local_user)
    monkeypatch.setattr(
        "app.dependencies.auth.PersonalUserService", fake_service_cls
    )

    user = await get_current_user(_FakeRequest(), credentials=None, session=None)

    assert user is local_user
    assert user.email == LOCAL_USER_EMAIL
    assert user.role == Role.ADMIN
    assert user.is_active is True
    # No se tocó JWT en absoluto.
    fake_service_cls.assert_called_once()
    fake_instance.ensure_local_user.assert_awaited_once()


@pytest.mark.asyncio
async def test_auth_enabled_still_requires_jwt_without_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Flag OFF (default): sin token sigue lanzando AuthenticationError."""
    monkeypatch.setattr(settings, "auth_disabled", False)

    with pytest.raises(AuthenticationError):
        await get_current_user(_FakeRequest(), credentials=None, session=None)


class FakeUserRepository:
    """Mini-repositorio en memoria (mismo contrato que UserRepository)."""

    def __init__(self) -> None:
        self._users: dict[str, User] = {}

    async def get_by_email(self, email: str) -> User | None:
        return self._users.get(email)

    async def create(self, user: User) -> User:
        self._users[user.email] = user
        return user


@pytest.mark.asyncio
async def test_personal_user_service_get_or_create_creates_once() -> None:
    repo = FakeUserRepository()
    service = PersonalUserService(repo)  # type: ignore[arg-type]

    first = await service.ensure_local_user()
    second = await service.ensure_local_user()

    assert first is second
    assert first.email == LOCAL_USER_EMAIL
    assert first.role == Role.ADMIN
    assert first.is_active is True
    assert first.is_verified is True
    assert len(repo._users) == 1


@pytest.mark.asyncio
async def test_personal_user_service_reuses_existing_row() -> None:
    repo = FakeUserRepository()
    existing = _local_admin()
    repo._users[existing.email] = existing
    service = PersonalUserService(repo)  # type: ignore[arg-type]

    user = await service.ensure_local_user()

    assert user is existing
    assert len(repo._users) == 1
