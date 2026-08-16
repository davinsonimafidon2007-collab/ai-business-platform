from __future__ import annotations

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

from app.core.exception_handlers import register_exception_handlers
from app.exceptions import (
    AuthenticationError,
    AuthorizationError,
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.providers.exceptions import (
    ProviderConnectionError,
    ProviderError,
    ProviderTimeoutError,
)


class SamplePayload(BaseModel):
    email: str = Field(min_length=3)


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/domain/user-not-found")
    async def raise_user_not_found() -> None:
        raise UserNotFoundError("User with id '123' was not found")

    @app.get("/domain/authentication")
    async def raise_authentication_error() -> None:
        raise AuthenticationError("Not authenticated")

    @app.get("/domain/authorization")
    async def raise_authorization_error() -> None:
        raise AuthorizationError("Insufficient permissions")

    @app.get("/domain/conflict")
    async def raise_conflict() -> None:
        raise UserAlreadyExistsError("User already exists")

    @app.get("/domain/invalid-credentials")
    async def raise_invalid_credentials() -> None:
        raise InvalidCredentialsError("Invalid email or password")

    @app.get("/http/unauthorized")
    async def raise_http_unauthorized() -> None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    @app.get("/http/forbidden")
    async def raise_http_forbidden() -> None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    @app.get("/http/not-found")
    async def raise_http_not_found() -> None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    @app.get("/provider/connection-error")
    async def raise_provider_connection_error() -> None:
        raise ProviderConnectionError("Connection failed", provider="mobile_de")

    @app.get("/provider/timeout")
    async def raise_provider_timeout() -> None:
        raise ProviderTimeoutError("Provider timed out", provider="autoscout24", timeout=30.0)

    @app.get("/provider/generic")
    async def raise_provider_generic() -> None:
        raise ProviderError("Generic provider failure", provider="test_provider")

    @app.get("/database/error")
    async def raise_database_error() -> None:
        raise SQLAlchemyError("Database connection failed")

    @app.get("/timeout/error")
    async def raise_timeout_error() -> None:
        raise TimeoutError("Operation timed out")

    @app.get("/unhandled")
    async def raise_unhandled() -> None:
        raise RuntimeError("unexpected failure")

    @app.post("/validation")
    async def validate_payload(payload: SamplePayload) -> SamplePayload:
        return payload

    return TestClient(app, raise_server_exceptions=False)


def assert_error_response(response, expected_status: int, expected_code: str):
    """Helper para verificar el formato de error estandarizado."""
    assert response.status_code == expected_status
    payload = response.json()
    assert payload["success"] is False
    assert "error" in payload
    assert payload["error"]["code"] == expected_code
    assert isinstance(payload["error"]["message"], str)
    assert len(payload["error"]["message"]) > 0


def test_domain_user_not_found_error(client: TestClient) -> None:
    response = client.get("/domain/user-not-found")
    assert_error_response(response, 404, "user_not_found")
    assert "User with id '123' was not found" in response.json()["error"]["message"]


def test_domain_authentication_error_includes_www_authenticate(client: TestClient) -> None:
    response = client.get("/domain/authentication")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["error"]["code"] == "authentication_error"


def test_domain_authorization_error(client: TestClient) -> None:
    response = client.get("/domain/authorization")
    assert_error_response(response, 403, "authorization_error")


def test_domain_conflict_error(client: TestClient) -> None:
    response = client.get("/domain/conflict")
    assert_error_response(response, 409, "user_already_exists")


def test_domain_invalid_credentials_error(client: TestClient) -> None:
    response = client.get("/domain/invalid-credentials")
    assert_error_response(response, 401, "invalid_credentials")


def test_http_exception_is_normalized(client: TestClient) -> None:
    response = client.get("/http/unauthorized")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["error"]["code"] == "authentication_error"


def test_http_forbidden_exception_is_normalized(client: TestClient) -> None:
    response = client.get("/http/forbidden")
    assert_error_response(response, 403, "authorization_error")


def test_http_not_found_exception_is_normalized(client: TestClient) -> None:
    response = client.get("/http/not-found")
    assert_error_response(response, 404, "not_found")


def test_validation_error_is_normalized(client: TestClient) -> None:
    response = client.post("/validation", json={"email": "a"})
    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    assert "email" in payload["error"]["message"]
    assert "details" in payload["error"]
    assert isinstance(payload["error"]["details"], list)


def test_unhandled_exception_returns_internal_error(client: TestClient) -> None:
    response = client.get("/unhandled")
    assert_error_response(response, 500, "internal_error")


def test_provider_connection_error(client: TestClient) -> None:
    response = client.get("/provider/connection-error")
    assert_error_response(response, 502, "provider_error")
    payload = response.json()
    assert payload["error"]["details"]["provider"] == "mobile_de"


def test_provider_timeout_error(client: TestClient) -> None:
    response = client.get("/provider/timeout")
    assert_error_response(response, 502, "provider_error")
    payload = response.json()
    assert payload["error"]["details"]["provider"] == "autoscout24"


def test_provider_generic_error(client: TestClient) -> None:
    response = client.get("/provider/generic")
    assert_error_response(response, 502, "provider_error")
    payload = response.json()
    assert payload["error"]["details"]["provider"] == "test_provider"


def test_sqlalchemy_error(client: TestClient) -> None:
    response = client.get("/database/error")
    assert_error_response(response, 500, "database_error")


def test_timeout_error(client: TestClient) -> None:
    response = client.get("/timeout/error")
    assert_error_response(response, 504, "timeout_error")


def test_error_response_has_request_id(client: TestClient) -> None:
    """Verifica que el request_id está presente en respuestas de error."""
    response = client.get("/domain/user-not-found")
    assert response.status_code == 404
    payload = response.json()
    # El request_id puede ser None si no hay RequestIdMiddleware registrado
    # en este test de unidad, pero el campo debe existir
    assert "request_id" in payload["error"]


def test_error_response_format_is_consistent(client: TestClient) -> None:
    """Verifica que el formato de error es consistente entre distintos endpoints."""
    endpoints = [
        ("/domain/user-not-found", 404, "user_not_found"),
        ("/domain/authentication", 401, "authentication_error"),
        ("/domain/authorization", 403, "authorization_error"),
        ("/domain/conflict", 409, "user_already_exists"),
        ("/domain/invalid-credentials", 401, "invalid_credentials"),
        ("/http/unauthorized", 401, "authentication_error"),
        ("/http/forbidden", 403, "authorization_error"),
        ("/http/not-found", 404, "not_found"),
        ("/provider/connection-error", 502, "provider_error"),
        ("/provider/timeout", 502, "provider_error"),
        ("/database/error", 500, "database_error"),
        ("/timeout/error", 504, "timeout_error"),
        ("/unhandled", 500, "internal_error"),
    ]

    for endpoint, expected_status, expected_code in endpoints:
        response = client.get(endpoint)
        assert_error_response(response, expected_status, expected_code)


def test_handler_order_overrides_exception_for_provider(client: TestClient) -> None:
    """ProviderError hereda de Exception, debe ser capturado por provider handler, no el genérico."""
    response = client.get("/provider/connection-error")
    assert response.status_code == 502  # provider specific, no 500
    assert response.json()["error"]["code"] == "provider_error"

