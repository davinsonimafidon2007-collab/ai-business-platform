"""PERSONAL.NOAUTH: flag AUTH_DISABLED off/on en get_current_user.

- Flag ON  → get_current_user devuelve el usuario local ADMIN sin mirar Bearer.
- Flag OFF → sigue exigiendo JWT (no debe romperse la auth actual).
- PersonalUserService.ensure_local_user  → get-or-create de la fila en users.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.core.local_user import LOCAL_USER_EMAIL, LOCAL_USER_ID_STR
from app.dependencies.auth import get_current_user, require_role
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


@pytest.mark.asyncio
async def test_app_mode_personal_alone_does_not_bypass_auth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PERS.CLOSE.1: app_mode=personal SIN auth_disabled no salta la auth.

    El bypass tiene una única fuente de verdad (``auth_disabled``). Antes había
    un branch paralelo que podía devolver ``None`` y romper rutas que exigen
    un ``User`` real.
    """
    monkeypatch.setattr(settings, "auth_disabled", False)
    monkeypatch.setattr(settings, "app_mode", "personal")

    with pytest.raises(AuthenticationError):
        await get_current_user(_FakeRequest(), credentials=None, session=None)


@pytest.mark.asyncio
async def test_get_current_user_never_returns_none_when_auth_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Flag ON + app_mode=personal → siempre un User real, nunca None."""
    monkeypatch.setattr(settings, "auth_disabled", True)
    monkeypatch.setattr(settings, "app_mode", "personal")

    local_user = _local_admin()
    fake_service_cls = MagicMock()
    fake_service_cls.return_value.ensure_local_user = AsyncMock(
        return_value=local_user
    )
    monkeypatch.setattr(
        "app.dependencies.auth.PersonalUserService", fake_service_cls
    )

    user = await get_current_user(_FakeRequest(), credentials=None, session=None)

    assert user is not None
    assert isinstance(user, User)
    assert user.id == LOCAL_USER_ID_STR


@pytest.mark.asyncio
async def test_auth_disabled_user_passes_admin_role_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """El usuario local es ADMIN → require_role(ADMIN) lo acepta."""
    monkeypatch.setattr(settings, "auth_disabled", True)

    local_user = _local_admin()
    fake_service_cls = MagicMock()
    fake_service_cls.return_value.ensure_local_user = AsyncMock(
        return_value=local_user
    )
    monkeypatch.setattr(
        "app.dependencies.auth.PersonalUserService", fake_service_cls
    )

    user = await get_current_user(_FakeRequest(), credentials=None, session=None)
    dependency = require_role(Role.ADMIN)

    assert await dependency(current_user=user) is user


@pytest.mark.asyncio
async def test_auth_disabled_inactive_local_user_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Si la fila local está desactivada, no se inyecta silenciosamente."""
    monkeypatch.setattr(settings, "auth_disabled", True)

    inactive = _local_admin()
    inactive.is_active = False
    fake_service_cls = MagicMock()
    fake_service_cls.return_value.ensure_local_user = AsyncMock(return_value=inactive)
    monkeypatch.setattr(
        "app.dependencies.auth.PersonalUserService", fake_service_cls
    )

    with pytest.raises(AuthenticationError):
        await get_current_user(_FakeRequest(), credentials=None, session=None)


def test_env_auth_disabled_does_not_leak_into_tests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """E2E.MANUAL.PASS.1: AUTH_DISABLED=true del OS no contamina la suite.

    En Docker con uso personal, compose inyecta AUTH_DISABLED=true en el
    entorno. Si ese valor se cuela en ENVIRONMENT=test, los tests que esperan
    401 empiezan a ver 200 (13 fallos observados). Solo el opt-in explícito
    AUTH_DISABLED_IN_TESTS debe permitirlo.
    """
    monkeypatch.setenv("AUTH_DISABLED", "true")
    monkeypatch.delenv("AUTH_DISABLED_IN_TESTS", raising=False)

    cfg = Settings(environment="test", auth_disabled=True)

    assert cfg.auth_disabled is False


def test_auth_disabled_opt_in_for_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    """Con AUTH_DISABLED_IN_TESTS=true sí se puede testear el flag ON."""
    monkeypatch.setenv("AUTH_DISABLED_IN_TESTS", "true")

    cfg = Settings(environment="test", auth_disabled=True)

    assert cfg.auth_disabled is True


def test_auth_disabled_forbidden_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """production + AUTH_DISABLED=true sin override → Settings no carga."""
    # Opt-in explícito: sin él, el guard anti-contaminación fuerza False.
    monkeypatch.setenv("AUTH_DISABLED_IN_TESTS", "true")

    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            auth_disabled=True,
            jwt_secret_key="x" * 40,
            cors_origins="https://app.example.com",
        )


def test_auth_disabled_strictly_forbidden_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AUTH_DISABLED=true en producción es estrictamente imposible (hard fail sin excepciones)."""
    monkeypatch.setenv("AUTH_DISABLED_IN_TESTS", "true")

    with pytest.raises(ValidationError) as exc_info:
        Settings(
            environment="production",
            auth_disabled=True,
            jwt_secret_key="x" * 40,
            cors_origins="https://app.example.com",
        )

    assert "CRITICAL SECURITY ERROR" in str(exc_info.value)


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
