from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_cors_disallowed_origin():
    """Verificar que orígenes no permitidos reciben respuesta sin la cabecera Access-Control-Allow-Origin."""
    response = client.options(
        "/health",
        headers={"Origin": "https://malicious-domain.com", "Access-Control-Request-Method": "GET"},
    )
    assert response.headers.get("access-control-allow-origin") != "https://malicious-domain.com"


def test_cors_allowed_origin():
    """Verificar que orígenes permitidos reciben la cabecera de CORS correcta."""
    allowed = settings.cors_origins_list[0] if settings.cors_origins_list else "http://localhost:3000"
    response = client.options(
        "/health",
        headers={"Origin": allowed, "Access-Control-Request-Method": "GET"},
    )
    assert response.headers.get("access-control-allow-origin") == allowed
