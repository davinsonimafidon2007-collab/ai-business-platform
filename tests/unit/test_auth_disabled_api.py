"""PERS.CLOSE.1: con AUTH_DISABLED=true una ruta de negocio no devuelve 401.

Criterio de aceptación 1/5: sin header ``Authorization``, la API responde
normalmente (el usuario local ADMIN se inyecta en ``get_current_user``) en vez
de cortar con 401 por falta de Bearer.

Se testea contra ``/api/v1/opportunities`` con el repositorio de datos mockeado:
lo que se verifica es la **capa de auth**, no la query real.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.local_user import LOCAL_USER_EMAIL, LOCAL_USER_ID_STR
from app.main import app
from app.models.role import Role
from app.models.user import User


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


@pytest.fixture
def _no_db(monkeypatch: pytest.MonkeyPatch):
    """Evita tocar Postgres: sesi��n y repositorios falsos."""
    from app.api.v1 import opportunities as opportunities_module
    from app.database import get_db_session

    async def _fake_session():
        yield MagicMock()

    app.dependency_overrides[get_db_session] = _fake_session

    fake_service_cls = MagicMock()
    fake_service_cls.return_value.ensure_local_user = AsyncMock(
        return_value=_local_admin()
    )
    monkeypatch.setattr(
        "app.dependencies.auth.PersonalUserService", fake_service_cls
    )

    fake_repo = MagicMock()
    fake_repo.list_filtered = AsyncMock(return_value=([], 0))
    monkeypatch.setattr(
        opportunities_module,
        "OpportunityRepository",
        MagicMock(return_value=fake_repo),
    )

    yield
    # Remover solo el override agregado; NO usar clear() para no borrar
    # overrides de otros tests (p. ej. mocks de get_current_user).
    if get_db_session in app.dependency_overrides:
        del app.dependency_overrides[get_db_session]


def test_business_route_no_401_when_auth_disabled(
    monkeypatch: pytest.MonkeyPatch, _no_db: None
) -> None:
    """Flag ON + sin Authorization → la respuesta NO es 401."""
    monkeypatch.setattr(settings, "auth_disabled", True)

    with TestClient(app) as client:
        response = client.get("/api/v1/opportunities?limit=1")

    assert response.status_code != 401, response.text


def test_business_route_is_401_when_auth_enabled(
    monkeypatch: pytest.MonkeyPatch, _no_db: None
) -> None:
    """Flag OFF + sin Authorization → sigue siendo 401 (no se rompió la auth)."""
    monkeypatch.setattr(settings, "auth_disabled", False)

    with TestClient(app) as client:
        response = client.get("/api/v1/opportunities?limit=1")

    assert response.status_code == 401, response.text
