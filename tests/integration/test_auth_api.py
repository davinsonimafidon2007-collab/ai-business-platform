from typing import Any

import pytest
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient

from app.api.v1 import auth as auth_module
from app.main import app
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.refresh_token_service import RefreshTokenService


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


@pytest.fixture
def client() -> TestClient:
    user_repository = FakeUserRepository()
    token_repository = FakeRefreshTokenRepository()
    auth_service = AuthService(user_repository)
    refresh_service = RefreshTokenService(token_repository)

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

    app.dependency_overrides[auth_module.get_auth_service] = override_get_auth_service
    app.dependency_overrides[auth_module.get_current_user] = override_get_current_user
    app.dependency_overrides[auth_module.get_refresh_token_service] = override_get_refresh_token_service
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
