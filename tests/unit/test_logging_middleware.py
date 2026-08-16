from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.logging import setup_logging
from app.middleware.logging_middleware import AccessLogMiddleware


@pytest.fixture(autouse=True)
def setup_test_logging():
    """Configura logging para tests."""
    with patch("app.core.logging.settings") as mock_settings, \
         patch("app.middleware.logging_middleware.settings") as mock_mw_settings:
        mock_settings.environment = "test"
        mock_settings.log_level = "DEBUG"
        mock_settings.log_json = False
        mock_settings.enable_access_log = True
        mock_mw_settings.enable_access_log = True
        mock_mw_settings.log_json = False
        setup_logging()
        yield


def test_access_log_middleware_logs_request():
    """Verifica que el middleware registra acceso."""
    app = FastAPI()
    app.add_middleware(AccessLogMiddleware)

    @app.get("/test")
    def test_endpoint():
        return {"message": "ok"}

    client = TestClient(app)

    with patch("app.middleware.logging_middleware.logger") as mock_logger:
        response = client.get("/test")

        assert response.status_code == 200
        # Verificar que se llamó a logger.info
        assert mock_logger.info.called


def test_access_log_middleware_disabled():
    """Verifica que el middleware no loguea si está deshabilitado."""
    app = FastAPI()

    @app.get("/test")
    def test_endpoint():
        return {"message": "ok"}

    client = TestClient(app)

    with patch("app.middleware.logging_middleware.settings") as mock_settings:
        mock_settings.enable_access_log = False

        with patch("app.middleware.logging_middleware.logger") as mock_logger:
            response = client.get("/test")
            assert response.status_code == 200
            # No debe loguear nada
            assert not mock_logger.info.called


def test_access_log_middleware_logs_error():
    """Verifica que el middleware registra errores (status 500)."""
    app = FastAPI()
    app.add_middleware(AccessLogMiddleware)

    @app.get("/error")
    def error_endpoint():
        raise ValueError("Test error")

    client = TestClient(app, raise_server_exceptions=False)

    with patch("app.middleware.logging_middleware.logger") as mock_logger:
        response = client.get("/error")

        assert response.status_code == 500
        # Debe haber llamado a logger.info incluso para errores (antes de que el exception handler responda)
        assert mock_logger.info.called


def test_access_log_json_format():
    """Verifica que el middleware puede loguear en formato JSON."""
    app = FastAPI()
    app.add_middleware(AccessLogMiddleware)

    @app.get("/test")
    def test_endpoint():
        return {"message": "ok"}

    client = TestClient(app)

    with patch("app.middleware.logging_middleware.settings") as mock_settings, \
         patch("app.middleware.logging_middleware.logger") as mock_logger:
        mock_settings.enable_access_log = True
        mock_settings.log_json = True

        response = client.get("/test")

        assert response.status_code == 200
        assert mock_logger.info.called
        # Verificar que el argumento del log es un JSON string
        call_args = mock_logger.info.call_args[0]
        assert len(call_args) == 1
        import json
        log_data = json.loads(call_args[0])
        assert "method" in log_data
        assert "path" in log_data
        assert "status" in log_data
        assert "duration_ms" in log_data


def test_access_log_middleware_with_post():
    """Verifica que el middleware funciona con POST requests."""
    app = FastAPI()
    app.add_middleware(AccessLogMiddleware)

    @app.post("/submit")
    def submit_endpoint():
        return {"result": "ok"}

    client = TestClient(app)

    with patch("app.middleware.logging_middleware.logger") as mock_logger:
        response = client.post("/submit", json={"data": "test"})
        assert response.status_code == 200
        assert mock_logger.info.called


def test_access_log_middleware_with_query_params():
    """Verifica que el middleware loguea query params."""
    app = FastAPI()
    app.add_middleware(AccessLogMiddleware)

    @app.get("/search")
    def search_endpoint(q: str = ""):
        return {"q": q}

    client = TestClient(app)

    with patch("app.middleware.logging_middleware.logger") as mock_logger:
        response = client.get("/search?q=bmw")
        assert response.status_code == 200
        assert mock_logger.info.called


def test_access_log_middleware_with_multiple_calls():
    """Verifica que el middleware funciona con múltiples llamadas."""
    app = FastAPI()
    app.add_middleware(AccessLogMiddleware)

    @app.get("/test")
    def test_endpoint():
        return {"message": "ok"}

    client = TestClient(app)

    with patch("app.middleware.logging_middleware.logger") as mock_logger:
        for _ in range(5):
            response = client.get("/test")
            assert response.status_code == 200

        # Debe haber 5 llamadas a logger.info
        assert mock_logger.info.call_count == 5

