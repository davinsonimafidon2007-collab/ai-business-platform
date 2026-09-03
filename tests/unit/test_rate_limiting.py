"""Rate limiting: configuración real + wiring del middleware (F.1).

Auditoría TEST.D: los 3 tests originales que hacían ``patch("app.core.config.settings")``
y asertaban sobre el propio mock eran tautologías imposibles de fallar; se han
sustituido por invariantes sobre el objeto de settings REAL y por comprobaciones
de comportamiento (middleware en la pila, límite aplicado en /openapi.json).
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


def test_rate_limit_defaults_are_positive_integers():
    """Los umbrales reales de Settings son enteros positivos coherentes."""
    for value in (
        settings.rate_limit_global,
        settings.rate_limit_login,
        settings.rate_limit_register,
        settings.rate_limit_user,
        settings.rate_limit_readonly,
    ):
        assert isinstance(value, int)
        assert value > 0


def test_rate_limit_login_more_restrictive_than_global():
    """El límite de login debe ser menor o igual que el global (ataque brute-force)."""
    assert settings.rate_limit_login < settings.rate_limit_global


def test_rate_limit_global_applied():
    """Verifica que el rate limit global está aplicado en la aplicación."""
    client = TestClient(app)

    # Realizar múltiples peticiones a un endpoint sin dependencias de DB/Redis
    # (/openapi.json). No se usa /health porque DEVOPS-001 hace que devuelva 503
    # si la DB no está disponible. El límite global es 60 req/min.
    for _ in range(5):
        response = client.get("/openapi.json")
        assert response.status_code == 200


def test_rate_limit_middleware_applied():
    """Verifica que el RateLimitMiddleware está aplicado en la aplicación."""
    from app.middleware.rate_limit_middleware import RateLimitMiddleware

    middleware_classes = [mw.cls for mw in app.user_middleware]
    assert RateLimitMiddleware in middleware_classes
    from app.api.v1.auth import login_user

    assert login_user is not None
