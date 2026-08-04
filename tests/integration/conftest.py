"""Fixtures compartidos de integration auth (Task C.5).

Patrón alineado con tests/unit/test_simulate_profit_endpoint.py:
override de get_current_user en lugar de tokens JWT reales.
"""

from __future__ import annotations

import pytest

from app.dependencies.auth import get_current_user
from app.main import app
from app.models.user import User


@pytest.fixture
def test_user() -> User:
    """Usuario de test con campos obligatorios del modelo User real.

    El __init__ de User rellena is_active, is_verified, role, created_at,
    updated_at e id si no se pasan.
    """
    return User(
        id="11111111-1111-1111-1111-111111111111",
        email="test@example.com",
        hashed_password="not-used-in-override",
    )


@pytest.fixture
def override_auth(test_user: User) -> User:
    """Override de get_current_user para endpoints autenticados.

    Hace yield del usuario y limpia el override al final.
    """
    async def _get_current_user() -> User:
        return test_user

    app.dependency_overrides[get_current_user] = _get_current_user
    yield test_user
    app.dependency_overrides.pop(get_current_user, None)