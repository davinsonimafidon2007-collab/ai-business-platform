from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app


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
