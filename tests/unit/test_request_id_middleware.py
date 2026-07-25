from __future__ import annotations

import logging
from unittest.mock import patch

import pytest
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse

from app.core.logging import setup_logging
from app.middleware.request_id import RequestIdMiddleware


@pytest.fixture(autouse=True)
def setup_test_logging():
    """Configura logging para tests."""
    with patch("app.core.logging.settings") as mock_settings:
        mock_settings.environment = "development"
        setup_logging()
        yield


def test_request_id_generated_when_not_provided():
    """Verifica que se genera un request_id cuando no se proporciona."""
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/test")
    def test_endpoint():
        return {"message": "ok"}

    client = TestClient(app)
    response = client.get("/test")

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"] != ""
    assert len(response.headers["X-Request-ID"]) == 36  # UUID length


def test_request_id_preserved_when_provided():
    """Verifica que se preserva el request_id cuando se proporciona."""
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/test")
    def test_endpoint():
        return {"message": "ok"}

    client = TestClient(app)
    custom_request_id = "custom-request-id-123"
    response = client.get("/test", headers={"X-Request-ID": custom_request_id})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == custom_request_id


def test_request_id_in_logs():
    """Verifica que el request_id aparece en los logs."""
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/test")
    def test_endpoint():
        return {"message": "ok"}

    client = TestClient(app)

    with patch("app.middleware.request_id.logger") as mock_logger:
        response = client.get("/test")
        
        assert response.status_code == 200
        assert mock_logger.info.call_count >= 2  # Al menos start y complete
        
        # Verificar que los logs incluyen request_id
        start_call = mock_logger.info.call_args_list[0]
        assert "request_id" in start_call.kwargs.get("extra", {})


def test_middleware_logs_request_details():
    """Verifica que el middleware registra método, ruta y status_code."""
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.post("/test", status_code=status.HTTP_201_CREATED)
    def test_post_endpoint():
        return {"message": "created"}

    client = TestClient(app)

    with patch("app.middleware.request_id.logger") as mock_logger:
        response = client.post("/test")
        
        assert response.status_code == 201
        
        # Verificar log de inicio
        start_call = mock_logger.info.call_args_list[0]
        assert start_call.kwargs["extra"]["method"] == "POST"
        assert start_call.kwargs["extra"]["path"] == "/test"
        
        # Verificar log de completado
        complete_call = mock_logger.info.call_args_list[1]
        assert complete_call.kwargs["extra"]["method"] == "POST"
        assert complete_call.kwargs["extra"]["path"] == "/test"
        assert complete_call.kwargs["extra"]["status_code"] == 201
        assert "process_time_ms" in complete_call.kwargs["extra"]


def test_middleware_handles_errors():
    """Verifica que el middleware registra errores no controlados."""
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/error")
    def error_endpoint():
        raise ValueError("Test error")

    client = TestClient(app, raise_server_exceptions=False)

    with patch("app.middleware.request_id.logger") as mock_logger:
        response = client.get("/error")
        
        # El error debe ser manejado por el exception handler de FastAPI
        assert response.status_code == 500
        
        # Verificar que se logueó el error
        error_call = mock_logger.error.call_args
        assert error_call is not None
        assert "request_id" in error_call.kwargs.get("extra", {})
        assert error_call.kwargs["extra"]["method"] == "GET"
        assert error_call.kwargs["extra"]["path"] == "/error"
        assert error_call.kwargs.get("exc_info") is True


def test_middleware_compatibility_with_exception_handlers():
    """Verifica que el middleware es compatible con los exception handlers existentes."""
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/not-found")
    def not_found_endpoint():
        raise HTTPException(status_code=404, detail="Not found")

    @app.get("/unauthorized")
    def unauthorized_endpoint():
        raise HTTPException(status_code=401, detail="Unauthorized")

    client = TestClient(app)

    # Verificar que las excepciones HTTP se manejan correctamente
    response_404 = client.get("/not-found")
    assert response_404.status_code == 404
    assert "X-Request-ID" in response_404.headers

    response_401 = client.get("/unauthorized")
    assert response_401.status_code == 401
    assert "X-Request-ID" in response_401.headers


def test_middleware_with_existing_endpoints():
    """Verifica que el middleware funciona con endpoints existentes."""
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/health")
    def health():
        return {"status": "operational"}

    @app.post("/auth/login")
    def login():
        return {"access_token": "test-token"}

    client = TestClient(app)

    # Health check
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "operational"}
    assert "X-Request-ID" in response.headers

    # Login
    response = client.post("/auth/login", json={"email": "test@example.com", "password": "password"})
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers


def test_request_id_in_response_headers_always():
    """Verifica que X-Request-ID siempre está presente en la respuesta."""
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/test")
    def test_endpoint():
        return {"message": "ok"}

    @app.post("/test")
    def test_post():
        return {"message": "created"}

    @app.put("/test")
    def test_put():
        return {"message": "updated"}

    @app.delete("/test")
    def test_delete():
        return {"message": "deleted"}

    client = TestClient(app)

    for method, endpoint in [
        (client.get, "/test"),
        (client.post, "/test"),
        (client.put, "/test"),
        (client.delete, "/test"),
    ]:
        response = method(endpoint)
        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) > 0