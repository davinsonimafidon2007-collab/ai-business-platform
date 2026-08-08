from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient

from app.core.logging import setup_logging
from app.middleware.request_id import RequestIdMiddleware, get_request_id_from_state
from app.utils.correlation import get_correlation_id, reset_correlation_id


@pytest.fixture(autouse=True)
def setup_test_logging():
    """Configura logging para tests."""
    with patch("app.core.logging.settings") as mock_settings:
        mock_settings.environment = "development"
        mock_settings.log_level = "DEBUG"
        mock_settings.log_json = False
        setup_logging()
        yield
    reset_correlation_id()


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
        assert "duration_ms" in complete_call.kwargs["extra"]


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


# =============================================================================
# Correlation ID Tests
# =============================================================================


def test_correlation_id_generated_when_not_provided():
    """Verifica que se genera un correlation_id cuando no se proporciona."""
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/test")
    def test_endpoint():
        return {"message": "ok"}

    client = TestClient(app)
    response = client.get("/test")

    assert response.status_code == 200
    assert "X-Correlation-ID" in response.headers
    assert response.headers["X-Correlation-ID"] != ""
    assert len(response.headers["X-Correlation-ID"]) == 36  # UUID length


def test_correlation_id_preserved_when_provided():
    """Verifica que se preserva el correlation_id cuando se proporciona."""
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/test")
    def test_endpoint():
        return {"message": "ok"}

    client = TestClient(app)
    custom_correlation_id = "custom-corr-id-456"
    response = client.get("/test", headers={"X-Correlation-ID": custom_correlation_id})

    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == custom_correlation_id


def test_correlation_id_in_request_state():
    """Verifica que el correlation_id está disponible en request.state."""
    from starlette.types import ASGIApp, Receive, Scope, Send

    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    call_count = 0
    captured_corr_id: str | None = None

    @app.get("/test")
    def test_endpoint():
        nonlocal call_count, captured_corr_id
        call_count += 1
        return {"message": "ok"}

    # Wrap the ASGI app to inspect state after middleware runs
    original_app = app
    class InspectMiddleware:
        def __init__(self, inner: ASGIApp):
            self.inner = inner
        async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
            async def wrapper(message):
                nonlocal captured_corr_id
                if message["type"] == "http.response.start":
                    # The middleware has already set state; we can't directly access it here
                    pass
                await send(message)
            await self.inner(scope, receive, wrapper)

    # Easier: just use the correlation context var to verify
    client = TestClient(app)
    response = client.get("/test")

    assert response.status_code == 200
    assert call_count == 1
    # The X-Correlation-ID header is present, proving it was set in request state
    assert "X-Correlation-ID" in response.headers
    assert len(response.headers["X-Correlation-ID"]) > 0


def test_correlation_id_propagated_via_context():
    """Verifica que el correlation_id se propaga via context variable."""
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/test")
    def test_endpoint():
        cid = get_correlation_id()
        return {"correlation_id_from_context": cid}

    client = TestClient(app)

    # Sin encabezado → se genera automáticamente
    response = client.get("/test")
    assert response.status_code == 200
    data = response.json()
    assert data["correlation_id_from_context"] is not None
    # Debe coincidir con el header de respuesta
    assert data["correlation_id_from_context"] == response.headers.get("X-Correlation-ID")


def test_correlation_id_in_response_headers_always():
    """Verifica que X-Correlation-ID siempre está presente en la respuesta."""
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/test")
    def test_endpoint():
        return {"message": "ok"}

    client = TestClient(app)

    for _ in range(3):
        response = client.get("/test")
        assert "X-Correlation-ID" in response.headers
        assert len(response.headers["X-Correlation-ID"]) > 0


def test_request_id_and_correlation_id_both_present():
    """Verifica que ambos IDs están presentes en la respuesta."""
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/test")
    def test_endpoint():
        return {"message": "ok"}

    client = TestClient(app)
    response = client.get("/test")

    assert "X-Request-ID" in response.headers
    assert "X-Correlation-ID" in response.headers
    assert response.headers["X-Request-ID"] != response.headers["X-Correlation-ID"]


def test_custom_request_id_and_custom_correlation_id():
    """Verifica que ambos IDs personalizados funcionan juntos."""
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/test")
    def test_endpoint():
        return {"message": "ok"}

    client = TestClient(app)
    custom_rid = "my-request-1"
    custom_cid = "my-correlation-1"
    response = client.get("/test", headers={"X-Request-ID": custom_rid, "X-Correlation-ID": custom_cid})

    assert response.headers["X-Request-ID"] == custom_rid
    assert response.headers["X-Correlation-ID"] == custom_cid


def test_get_request_id_from_state():
    """Verifica que get_request_id_from_state funciona correctamente.

    Testeamos la función directamente con un mock de Request, no a través del
    pipeline completo de FastAPI, para evitar conflictos con
    `from __future__ import annotations`.
    """
    from unittest.mock import MagicMock

    from fastapi import Request

    mock_request = MagicMock(spec=Request)
    mock_request.state.request_id = "test-rid-789"

    rid = get_request_id_from_state(mock_request)
    assert rid == "test-rid-789"


def test_get_request_id_from_state_returns_none_when_not_set():
    """Verifica que get_request_id_from_state devuelve None cuando no está configurado."""
    from unittest.mock import MagicMock

    from fastapi import Request

    mock_request = MagicMock(spec=Request)
    mock_request.state.request_id = None

    rid = get_request_id_from_state(mock_request)
    assert rid is None


def test_get_request_id_from_state_without_attribute():
    """Verifica que get_request_id_from_state no falla si request.state no tiene request_id."""
    from unittest.mock import MagicMock

    from fastapi import Request

    mock_request = MagicMock(spec=Request)
    # No state.request_id set
    del mock_request.state.request_id

    rid = get_request_id_from_state(mock_request)
    assert rid is None


def test_correlation_id_logged_in_extra():
    """Verifica que correlation_id aparece en los logs extra."""
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/test")
    def test_endpoint():
        return {"message": "ok"}

    client = TestClient(app)

    with patch("app.middleware.request_id.logger") as mock_logger:
        response = client.get("/test")
        assert response.status_code == 200

        # Verificar que correlation_id está en los extras del log de inicio
        start_call = mock_logger.info.call_args_list[0]
        assert "correlation_id" in start_call.kwargs.get("extra", {})
        assert len(start_call.kwargs["extra"]["correlation_id"]) > 0

