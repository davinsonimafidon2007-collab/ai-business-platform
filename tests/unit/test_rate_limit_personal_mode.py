"""AUDIT.AUTH — rate limit por rol también en modo personal (AUTH_DISABLED).

Antes: con AUTH_DISABLED=true no había request.state.user, así que TODO el
tráfico caía en el cubo anónimo por IP (rate_limit_global=60/min) aunque el
rol efectivo es ADMIN. Ahora el limiter usa la identidad fija del usuario
local con su límite de rol (premium), igual que un ADMIN JWT en multi-user.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, Request
from starlette.responses import Response

from app.core.config import settings
from app.middleware.rate_limit_middleware import (
    RATE_LIMIT_MODE_HEADER,
    RateLimitMiddleware,
)


def _request(path: str) -> MagicMock:
    request = MagicMock(spec=Request)
    request.url.path = path
    request.client.host = "127.0.0.1"
    request.state.user = None
    request.state.auth_method = None
    request.method = "GET"
    request.headers = {}
    return request


@pytest.fixture
def middleware() -> RateLimitMiddleware:
    return RateLimitMiddleware(FastAPI(), window_seconds=60)


@pytest.mark.asyncio
async def test_personal_mode_uses_admin_identity_not_ip_bucket(
    middleware: RateLimitMiddleware, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dos rutas distintas suman al cubo del usuario local (premium=120).

    Con el cubo IP genérico (60/min compartido) la segunda mitad habría dado
    429; con la identidad ADMIN local las 100 peticiones pasan.
    """
    monkeypatch.setattr(settings, "auth_disabled", True)
    call_next = AsyncMock(return_value=Response())

    for i in range(50):
        resp = await middleware.dispatch(_request(f"/api/v1/ruta-a?q={i}"), call_next)
        assert resp.status_code == 200, f"ruta-a petición {i}"
    for i in range(50):
        resp = await middleware.dispatch(_request(f"/api/v1/ruta-b?q={i}"), call_next)
        assert resp.status_code == 200, f"ruta-b petición {i}"


@pytest.mark.asyncio
async def test_personal_mode_still_enforces_role_ceiling(
    middleware: RateLimitMiddleware, monkeypatch: pytest.MonkeyPatch
) -> None:
    """El modo personal NO elimina el límite: superado el techo ADMIN → 429."""
    monkeypatch.setattr(settings, "auth_disabled", True)
    call_next = AsyncMock(return_value=Response())

    saw_429 = False
    total = settings.rate_limit_premium + 25
    for i in range(total):
        # Rutas distintas para saltarse el cubo por-endpoint y golpear solo
        # el cubo de identidad.
        resp = await middleware.dispatch(_request(f"/api/v1/ruta-{i}"), call_next)
        if resp.status_code == 429:
            assert i >= settings.rate_limit_premium - 5  # tolerancia ventana
            assert RATE_LIMIT_MODE_HEADER in resp.headers
            saw_429 = True
            break
    assert saw_429, "el cubo de identidad debería agotarse con techo premium"


@pytest.mark.asyncio
async def test_multiuser_mode_keeps_anonymous_ip_bucket(
    middleware: RateLimitMiddleware, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Multi-user sin token: comportamiento original por IP intacto."""
    monkeypatch.setattr(settings, "auth_disabled", False)
    call_next = AsyncMock(return_value=Response())

    status_codes = []
    for i in range(settings.rate_limit_global + 10):
        resp = await middleware.dispatch(_request(f"/api/v1/otra-{i}"), call_next)
        status_codes.append(resp.status_code)

    # El cubo IP compartido se agota en rate_limit_global peticiones.
    assert status_codes.count(200) == settings.rate_limit_global
    assert 429 in status_codes
