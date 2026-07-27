from typing import Any

import pytest
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient

from app.api.v1 import auth as auth_module
from app.main import app
from app.models.user import User
from app.models.verification_token import VerificationToken
from app.repositories.verification_token_repository import VerificationTokenRepository
from app.services.auth_service import AuthService
from app.services.refresh_token_service import RefreshTokenService
from app.services.verification_service import VerificationService


class FakeUserRepository:
    def __init__(self) -> None:
        self._users: dict[str, User] = {}

    async def get_by_email(self, email: str) -> User | None:
        return self._users.get(email)

    async def get_by_id(self, user_id: str | Any) -> User | None:
        return next((user for user in self._users.values() if str(user.id) == str(user_id)), None)

    async def create(self, user: User) -> User:
        self._users[user.email] = user
        return user

    async def update(self, user: User) -> User:
        self._users[user.email] = user
        return user


class FakeRefreshTokenRepository:
    def __init__(self) -> None:
        self._tokens: dict[str, str] = {}

    async def create(self, refresh_token) -> None:
        self._tokens[refresh_token.token] = refresh_token.user_id

    async def get_by_token(self, token: str):
        from app.models.refresh_token import RefreshToken
        if token not in self._tokens:
            return None
        return RefreshToken(token=token, user_id=self._tokens[token])

    async def revoke_by_token(self, token: str) -> None:
        if token in self._tokens:
            del self._tokens[token]

    async def revoke_all_by_user_id(self, user_id: str) -> None:
        self._tokens = {token: uid for token, uid in self._tokens.items() if uid != user_id}


class FakeVerificationTokenRepository:
    def __init__(self) -> None:
        self._tokens: list[VerificationToken] = []

    async def create(self, token: VerificationToken) -> VerificationToken:
        self._tokens.append(token)
        return token

    async def get_by_token(self, token: str) -> VerificationToken | None:
        return next((t for t in self._tokens if t.token == token), None)

    async def get_valid_by_user_id(self, user_id: str) -> VerificationToken | None:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        valid = [t for t in self._tokens if t.user_id == user_id and not t.is_used and t.expires_at > now]
        return valid[-1] if valid else None

    async def mark_as_used(self, token: VerificationToken) -> VerificationToken:
        from datetime import datetime, timezone
        token.is_used = True
        token.used_at = datetime.now(timezone.utc)
        return token


user_repository = FakeUserRepository()
token_repository = FakeRefreshTokenRepository()
verification_token_repository = FakeVerificationTokenRepository()
auth_service = AuthService(user_repository)
refresh_service = RefreshTokenService(token_repository)
verification_service = VerificationService(
    user_repository=user_repository,
    token_repository=verification_token_repository,
    email_provider=None,
)


@pytest.fixture
def client() -> TestClient:
    # Clear state between tests
    user_repository._users.clear()
    token_repository._tokens.clear()
    verification_token_repository._tokens.clear()

    async def override_get_auth_service() -> AuthService:
        return auth_service

    async def override_get_current_user(request: Request) -> User:
        authorization = request.headers.get("authorization", "")
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Not authenticated")

        token = authorization.split(" ", 1)[1]
        try:
            payload = auth_service.decode_access_token(token)
        except Exception as exc:
            raise HTTPException(status_code=401, detail="Invalid or expired token") from exc

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = await user_repository.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    async def override_get_refresh_token_service() -> RefreshTokenService:
        return refresh_service

    async def override_get_verification_service() -> VerificationService:
        return verification_service

    app.dependency_overrides[auth_module.get_auth_service] = override_get_auth_service
    app.dependency_overrides[auth_module.get_current_user] = override_get_current_user
    app.dependency_overrides[auth_module.get_refresh_token_service] = override_get_refresh_token_service
    app.dependency_overrides[auth_module.get_verification_service] = override_get_verification_service
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_register_and_login_user(client: TestClient) -> None:
    register_response = client.post(
        "/auth/register",
        json={"email": "auth@example.com", "password": "secret123"},
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={"email": "auth@example.com", "password": "secret123"},
    )
    assert login_response.status_code == 200
    payload = login_response.json()
    assert "access_token" in payload

    me_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {payload['access_token']}"},
    )
    assert me_response.status_code == 200


def test_access_without_token_is_forbidden(client: TestClient) -> None:
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_invalid_token_is_rejected(client: TestClient) -> None:
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Tests Email Verification
# ---------------------------------------------------------------------------


def test_request_verification_requires_auth(client: TestClient) -> None:
    """Verifica que el endpoint request-verification requiere autenticación."""
    response = client.post("/auth/request-verification")
    assert response.status_code == 401


def test_request_and_verify_email(client: TestClient) -> None:
    """Verifica el flujo completo: registrar, solicitar verificación y confirmar."""
    # 1. Registrar usuario
    register_response = client.post(
        "/auth/register",
        json={"email": "verify@example.com", "password": "secret123"},
    )
    assert register_response.status_code == 201
    user_data = register_response.json()
    assert user_data["is_verified"] is False

    # 2. Login para obtener token
    login_response = client.post(
        "/auth/login",
        json={"email": "verify@example.com", "password": "secret123"},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]

    # 3. Solicitar verificación
    request_response = client.post(
        "/auth/request-verification",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert request_response.status_code == 200
    assert request_response.json()["message"] == "Verification email sent"

    # 4. Obtener el token generado (acceso al repositorio fake)
    token_record = verification_token_repository._tokens[0]
    raw_token = token_record.token

    # 5. Confirmar verificación
    verify_response = client.post(
        "/auth/verify",
        json={"token": raw_token},
    )
    assert verify_response.status_code == 200
    assert verify_response.json()["message"] == "Email verified successfully"

    # 6. Verificar que el usuario ahora está verificado
    me_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["is_verified"] is True


def test_verify_with_expired_token_returns_error(client: TestClient) -> None:
    """Verifica que un token expirado devuelve error."""
    from datetime import datetime, timedelta, timezone

    # Registrar y login
    client.post(
        "/auth/register",
        json={"email": "expired@example.com", "password": "secret123"},
    )
    login_response = client.post(
        "/auth/login",
        json={"email": "expired@example.com", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    # Solicitar verificación
    client.post(
        "/auth/request-verification",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    # Forzar expiración del token
    token_record = verification_token_repository._tokens[0]
    token_record.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)

    # Confirmar con token expirado
    verify_response = client.post(
        "/auth/verify",
        json={"token": token_record.token},
    )
    assert verify_response.status_code == 400
    response_json = verify_response.json()
    assert "error" in response_json
    assert "expired" in response_json["error"]["message"].lower()


def test_verify_with_already_used_token_returns_error(client: TestClient) -> None:
    """Verifica que un token ya usado devuelve error."""
    # Registrar y login
    client.post(
        "/auth/register",
        json={"email": "used@example.com", "password": "secret123"},
    )
    login_response = client.post(
        "/auth/login",
        json={"email": "used@example.com", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    # Solicitar y confirmar verificación
    client.post(
        "/auth/request-verification",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    token_record = verification_token_repository._tokens[0]

    # Primera confirmación (debe funcionar)
    client.post("/auth/verify", json={"token": token_record.token})

    # Segunda confirmación con el mismo token (debe fallar)
    verify_response = client.post(
        "/auth/verify",
        json={"token": token_record.token},
    )
    assert verify_response.status_code == 400
    response_json = verify_response.json()
    assert "error" in response_json
    assert "used" in response_json["error"]["message"].lower()


def test_verify_with_invalid_token_returns_error(client: TestClient) -> None:
    """Verifica que un token inválido devuelve error."""
    verify_response = client.post(
        "/auth/verify",
        json={"token": "invalid-token-that-does-not-exist"},
    )
    assert verify_response.status_code == 404
    response_json = verify_response.json()
    assert "error" in response_json
    assert "not found" in response_json["error"]["message"].lower()
