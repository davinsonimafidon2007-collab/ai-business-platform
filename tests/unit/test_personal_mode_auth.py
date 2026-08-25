"""AUDIT.AUTH — pruebas de autenticación/autorización para AMBOS modos.

Modo personal (AUTH_DISABLED=true):
- entrada directa: /auth/me responde sin Authorization;
- usuario personal persistente (get-or-create) y seguro ante carreras;
- roles funcionando: el usuario local es ADMIN y supera todos los gates.

Modo multi-user (AUTH_DISABLED=false):
- sin token → 401; JWT Bearer válido → 200; cookie access_token → 200;
- token basura → 401; RBAC por rol/permiso en la capa de dependencias.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

import app.dependencies.auth as dependencies_auth_module
import app.middleware.authentication_middleware as authentication_middleware_module
from app.core.config import settings
from app.core.local_user import LOCAL_USER_EMAIL, LOCAL_USER_ID_STR
from app.database import get_db_session
from app.dependencies.auth import (
    require_admin,
    require_manage_users,
    require_permission,
    require_search,
    require_view_admin,
)
from app.exceptions import AuthorizationError
from app.main import app
from app.models.role import Role
from app.models.user import User
from app.services.auth_service import AuthService


def _user(role: Role, *, is_active: bool = True) -> User:
    return User(
        id=LOCAL_USER_ID_STR if role == Role.ADMIN else "00000000-0000-4000-8000-000000000002",
        email=LOCAL_USER_EMAIL if role == Role.ADMIN else "member@example.com",
        hashed_password="",
        full_name="Test User",
        is_active=is_active,
        is_verified=True,
        role=role,
    )


def _with_timestamps(user: User) -> User:
    # UserRead exige datetimes; sin flush de BD hay que rellenarlos a mano.
    now = datetime.now(UTC)
    user.created_at = now
    user.updated_at = now
    return user


@pytest.fixture(autouse=True)
def _auth_on(monkeypatch: pytest.MonkeyPatch):
    """Los tests ajustan el flag explícitamente; por defecto multi-user ON."""
    monkeypatch.setattr(settings, "auth_disabled", False)


@pytest.fixture
def _no_db(monkeypatch: pytest.MonkeyPatch):
    """Evita Postgres/Redis/scheduler en el ciclo de vida del TestClient."""
    monkeypatch.setattr("app.core.redis.init_redis", AsyncMock())
    monkeypatch.setattr("app.core.redis.close_redis", AsyncMock())
    monkeypatch.setattr("app.database.db_manager.init", AsyncMock())
    monkeypatch.setattr("app.database.db_manager.shutdown", AsyncMock())

    @asynccontextmanager
    async def _fake_cm():
        yield MagicMock()

    monkeypatch.setattr("app.database.db_manager.get_session", _fake_cm)

    async def _fake_session():
        yield MagicMock()

    app.dependency_overrides[get_db_session] = _fake_session
    monkeypatch.setattr(settings, "enable_scheduler", False)
    yield
    app.dependency_overrides.pop(get_db_session, None)


def _stub_personal_user(
    monkeypatch: pytest.MonkeyPatch, user: User | None = None
) -> None:
    """Sustituye PersonalUserService para no tocar la tabla users real."""
    fake_service_cls = MagicMock()
    fake_service_cls.return_value.ensure_local_user = AsyncMock(
        return_value=user if user is not None else _with_timestamps(_user(Role.ADMIN))
    )
    monkeypatch.setattr(
        dependencies_auth_module, "PersonalUserService", fake_service_cls
    )


# ─────────────────────────── Modo personal ───────────────────────────


def test_me_without_token_returns_local_admin_when_auth_disabled(
    monkeypatch: pytest.MonkeyPatch, _no_db: None
) -> None:
    """Entrada directa: sin header Authorization la ruta protegida responde 200."""
    monkeypatch.setattr(settings, "auth_disabled", True)
    _stub_personal_user(monkeypatch)

    with TestClient(app) as client:
        resp = client.get("/api/v1/auth/me")

    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == LOCAL_USER_EMAIL
    # Contrato con el frontend: el wire format del rol es el VALUE ("admin").
    assert body["role"] == "admin"


def test_inactive_local_user_is_rejected(
    monkeypatch: pytest.MonkeyPatch, _no_db: None
) -> None:
    """Si el usuario local está inactivo no se inyecta: 401, no bypass."""
    monkeypatch.setattr(settings, "auth_disabled", True)
    inactive = _with_timestamps(_user(Role.ADMIN, is_active=False))
    _stub_personal_user(monkeypatch, inactive)

    with TestClient(app) as client:
        resp = client.get("/api/v1/auth/me")

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_ensure_local_user_is_race_safe() -> None:
    """Dos primeras peticiones simultáneas: IntegrityError → reusa la fila."""
    created = _user(Role.ADMIN)

    repo = MagicMock()
    repo.get_by_email = AsyncMock(side_effect=[None, created])
    repo.create = AsyncMock(side_effect=IntegrityError("dup", None, Exception()))
    repo.session = MagicMock()
    repo.session.rollback = AsyncMock()

    from app.services.personal_user_service import PersonalUserService

    service = PersonalUserService(repo)
    result = await service.ensure_local_user()

    assert result is created
    repo.session.rollback.assert_awaited_once()


# ─────────────────────────── Modo multi-user ──────────────────────────


def _stub_jwt_user(
    monkeypatch: pytest.MonkeyPatch, role: Role = Role.USER
) -> tuple[User, str]:
    """Stub de UserService usado por middleware y dependencias (sin BD)."""
    target_user = _with_timestamps(_user(role))
    token = AuthService(MagicMock()).create_access_token(user_id=target_user.id)

    class _StubUserService:
        def __init__(self, _repository) -> None:
            pass

        async def get_user(self, _user_id: str) -> User:
            return target_user

    monkeypatch.setattr(dependencies_auth_module, "UserService", _StubUserService)
    monkeypatch.setattr(
        authentication_middleware_module, "UserService", _StubUserService
    )
    return target_user, token


def test_me_requires_token_in_multiuser_mode(_no_db: None) -> None:
    """Multi-user: sin credenciales la ruta protegida sigue siendo 401."""
    with TestClient(app) as client:
        resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_me_with_bearer_token_in_multiuser_mode(
    monkeypatch: pytest.MonkeyPatch, _no_db: None
) -> None:
    """Multi-user: JWT Bearer válido autentica (flujo preservado)."""
    user, token = _stub_jwt_user(monkeypatch, Role.USER)

    with TestClient(app) as client:
        resp = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == user.email
    assert body["role"] == "user"


def test_me_with_cookie_token_in_multiuser_mode(
    monkeypatch: pytest.MonkeyPatch, _no_db: None
) -> None:
    """Multi-user: el fallback a cookie httponly también autentica."""
    _target, token = _stub_jwt_user(monkeypatch, Role.USER)

    with TestClient(app) as client:
        resp = client.get("/api/v1/auth/me", cookies={"access_token": token})

    assert resp.status_code == 200


def test_garbage_bearer_token_rejected_401(_no_db: None) -> None:
    """Multi-user: token inválido lo corta el middleware con 401."""
    with TestClient(app) as client:
        resp = client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-jwt"}
        )
    assert resp.status_code == 401


# ───────────────────────────── RBAC (roles) ───────────────────────────


@pytest.mark.asyncio
async def test_require_role_blocks_non_admin() -> None:
    dependency = require_admin()
    with pytest.raises(AuthorizationError):
        await dependency(current_user=_with_timestamps(_user(Role.USER)))


@pytest.mark.asyncio
async def test_user_lacks_manage_users_permission() -> None:
    """USER tiene manage_own_api_keys pero NO manage_users → 403."""
    dependency = require_manage_users()
    with pytest.raises(AuthorizationError):
        await dependency(current_user=_with_timestamps(_user(Role.USER)))


@pytest.mark.asyncio
async def test_local_admin_passes_every_permission_gate() -> None:
    """Modo personal/multi-user: el ADMIN supera todos los gates de permisos."""
    admin = _with_timestamps(_user(Role.ADMIN))
    for gate in (
        require_admin(),
        require_manage_users(),
        require_search(),
        require_view_admin(),
        require_permission("manage_roles"),
        require_permission("manage_api_keys"),
        require_permission("view_audit_logs"),
        require_permission("manage_own_api_keys"),
    ):
        resolved = await gate(current_user=admin)
        assert resolved.role == Role.ADMIN
