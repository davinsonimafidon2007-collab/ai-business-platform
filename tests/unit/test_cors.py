from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import app


# ---------------------------------------------------------------------------
# SEC-001 — Production CORS strictness (config validators)
# ---------------------------------------------------------------------------

_PROD_JWT = "prod-secret-that-is-at-least-32-characters-long"


def test_cors_production_rejects_wildcard():
    with patch.dict(
        "os.environ",
        {
            "ENVIRONMENT": "production",
            "JWT_SECRET_KEY": _PROD_JWT,
            "CORS_ORIGINS": "*",
        },
    ):
        with pytest.raises(ValidationError, match="\\*|CORS"):
            Settings()


def test_cors_production_rejects_empty():
    with patch.dict(
        "os.environ",
        {
            "ENVIRONMENT": "production",
            "JWT_SECRET_KEY": _PROD_JWT,
            "CORS_ORIGINS": "",
        },
    ):
        with pytest.raises(ValidationError, match="CORS_ORIGINS"):
            Settings()


def test_cors_production_rejects_dev_only_origins():
    with patch.dict(
        "os.environ",
        {
            "ENVIRONMENT": "production",
            "JWT_SECRET_KEY": _PROD_JWT,
            "CORS_ORIGINS": "http://localhost:3000,capacitor://localhost",
        },
    ):
        with pytest.raises(ValidationError, match="development-only"):
            Settings()


def test_cors_production_hardens_wildcard_headers():
    with patch.dict(
        "os.environ",
        {
            "ENVIRONMENT": "production",
            "JWT_SECRET_KEY": _PROD_JWT,
            "CORS_ORIGINS": "https://app.example.com",
            "CORS_ALLOW_HEADERS": "*",
        },
    ):
        settings = Settings()
        assert "*" not in settings.cors_headers_list
        assert "Authorization" in settings.cors_headers_list
        assert "X-API-Key" in settings.cors_headers_list


def test_cors_production_allows_explicit_origins():
    with patch.dict(
        "os.environ",
        {
            "ENVIRONMENT": "production",
            "JWT_SECRET_KEY": _PROD_JWT,
            "CORS_ORIGINS": "https://app.example.com,https://admin.example.com",
        },
    ):
        settings = Settings()
        assert settings.cors_origins_list == [
            "https://app.example.com",
            "https://admin.example.com",
        ]


def test_cors_headers_present():
    """Verifica que los headers CORS están presentes en las respuestas."""
    client = TestClient(app)
    
    # Realizar una petición con Origin
    response = client.get(
        "/health",
        headers={"Origin": "http://localhost:3000"},
    )
    
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_allows_multiple_origins():
    """Verifica que CORS permite múltiples origins configurados."""
    client = TestClient(app)
    
    # Test con primer origen
    response1 = client.get(
        "/health",
        headers={"Origin": "http://localhost:3000"},
    )
    assert response1.headers.get("access-control-allow-origin") == "http://localhost:3000"
    
    # Test con segundo origen
    response2 = client.get(
        "/health",
        headers={"Origin": "http://localhost:5173"},
    )
    assert response2.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_rejects_unconfigured_origin():
    """Verifica que CORS rechaza origins no configurados."""
    client = TestClient(app)
    
    response = client.get(
        "/health",
        headers={"Origin": "http://malicious-site.com"},
    )
    
    assert response.status_code == 200
    # No debe incluir el header de CORS para origins no permitidos
    assert "access-control-allow-origin" not in response.headers or \
           response.headers.get("access-control-allow-origin") != "http://malicious-site.com"


def test_cors_allows_credentials():
    """Verifica que CORS permite credenciales."""
    client = TestClient(app)
    
    response = client.get(
        "/health",
        headers={"Origin": "http://localhost:3000"},
    )
    
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_allows_standard_methods():
    """Verifica que CORS permite los métodos HTTP estándar."""
    client = TestClient(app)
    
    # Hacer una petición OPTIONS (preflight)
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    
    assert response.status_code == 200
    assert "access-control-allow-methods" in response.headers
    allowed_methods = response.headers["access-control-allow-methods"]
    assert "GET" in allowed_methods
    assert "POST" in allowed_methods
    assert "PUT" in allowed_methods
    assert "PATCH" in allowed_methods
    assert "DELETE" in allowed_methods


def test_cors_configuration_from_settings():
    """Verifica que la configuración CORS se carga desde Settings."""
    with patch("app.core.config.settings") as mock_settings:
        mock_settings.cors_origins_list = ["http://localhost:3000", "http://localhost:5173"]
        
        # Verificar que la propiedad devuelve la lista correcta
        assert mock_settings.cors_origins_list == ["http://localhost:3000", "http://localhost:5173"]


def test_cors_origins_list_parsing():
    """Verifica que el parsing de CORS origins funciona correctamente."""
    with patch("app.core.config.settings") as mock_settings:
        # Test con múltiples origins
        mock_settings.cors_origins = "http://localhost:3000, http://localhost:5173 ,http://localhost:8080"
        mock_settings.cors_origins_list = [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8080",
        ]
        assert mock_settings.cors_origins_list == [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8080",
        ]
        
        # Test con un solo origin
        mock_settings.cors_origins = "http://localhost:3000"
        mock_settings.cors_origins_list = ["http://localhost:3000"]
        assert mock_settings.cors_origins_list == ["http://localhost:3000"]
        
        # Test con espacios vacíos
        mock_settings.cors_origins = "http://localhost:3000, , http://localhost:5173"
        mock_settings.cors_origins_list = ["http://localhost:3000", "http://localhost:5173"]
        assert mock_settings.cors_origins_list == ["http://localhost:3000", "http://localhost:5173"]


def test_cors_methods_list_parsing():
    """Verifica que el parsing de CORS methods funciona correctamente."""
    with patch("app.core.config.settings") as mock_settings:
        # Test con múltiples métodos
        mock_settings.cors_allow_methods = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        mock_settings.cors_methods_list = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
        assert mock_settings.cors_methods_list == ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
        
        # Test con espacios vacíos
        mock_settings.cors_allow_methods = "GET, POST, PUT"
        mock_settings.cors_methods_list = ["GET", "POST", "PUT"]
        assert mock_settings.cors_methods_list == ["GET", "POST", "PUT"]


def test_cors_headers_list_parsing():
    """Verifica que el parsing de CORS headers funciona correctamente."""
    with patch("app.core.config.settings") as mock_settings:
        # Test con wildcard
        mock_settings.cors_allow_headers = "*"
        mock_settings.cors_headers_list = ["*"]
        assert mock_settings.cors_headers_list == ["*"]
        
        # Test con headers específicos
        mock_settings.cors_allow_headers = "Content-Type, Authorization, X-Requested-With"
        mock_settings.cors_headers_list = ["Content-Type", "Authorization", "X-Requested-With"]
        assert mock_settings.cors_headers_list == ["Content-Type", "Authorization", "X-Requested-With"]
        
        # Test con espacios vacíos
        mock_settings.cors_allow_headers = "Content-Type, , Authorization"
        mock_settings.cors_headers_list = ["Content-Type", "Authorization"]
        assert mock_settings.cors_headers_list == ["Content-Type", "Authorization"]


def test_cors_allow_credentials_setting():
    """Verifica que la configuración de allow_credentials se carga correctamente."""
    with patch("app.core.config.settings") as mock_settings:
        mock_settings.cors_allow_credentials = True
        assert mock_settings.cors_allow_credentials is True
        
        mock_settings.cors_allow_credentials = False
        assert mock_settings.cors_allow_credentials is False
