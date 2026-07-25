import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException

from app.core.exception_handlers import register_exception_handlers
from app.exceptions import (
    AuthenticationError,
    AuthorizationError,
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
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

    @app.get("/unhandled")
    async def raise_unhandled() -> None:
        raise RuntimeError("unexpected failure")

    @app.post("/validation")
    async def validate_payload(payload: SamplePayload) -> SamplePayload:
        return payload

    return TestClient(app, raise_server_exceptions=False)


def test_domain_user_not_found_error(client: TestClient) -> None:
    response = client.get("/domain/user-not-found")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "User with id '123' was not found",
        "code": "user_not_found",
    }


def test_domain_authentication_error_includes_www_authenticate(client: TestClient) -> None:
    response = client.get("/domain/authentication")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {
        "detail": "Not authenticated",
        "code": "authentication_error",
    }


def test_domain_authorization_error(client: TestClient) -> None:
    response = client.get("/domain/authorization")

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Insufficient permissions",
        "code": "authorization_error",
    }


def test_domain_conflict_error(client: TestClient) -> None:
    response = client.get("/domain/conflict")

    assert response.status_code == 409
    assert response.json() == {
        "detail": "User already exists",
        "code": "user_already_exists",
    }


def test_domain_invalid_credentials_error(client: TestClient) -> None:
    response = client.get("/domain/invalid-credentials")

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid email or password",
        "code": "invalid_credentials",
    }


def test_http_exception_is_normalized(client: TestClient) -> None:
    response = client.get("/http/unauthorized")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {
        "detail": "Not authenticated",
        "code": "authentication_error",
    }


def test_http_forbidden_exception_is_normalized(client: TestClient) -> None:
    response = client.get("/http/forbidden")

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Forbidden",
        "code": "authorization_error",
    }


def test_validation_error_is_normalized(client: TestClient) -> None:
    response = client.post("/validation", json={"email": "a"})

    assert response.status_code == 422
    payload = response.json()
    assert payload["code"] == "validation_error"
    assert "email" in payload["detail"]


def test_unhandled_exception_returns_internal_error(client: TestClient) -> None:
    response = client.get("/unhandled")

    assert response.status_code == 500
    assert response.json()["code"] == "internal_error"
    assert "unexpected failure" in response.json()["detail"]
