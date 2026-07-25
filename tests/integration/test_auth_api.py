from typing import Any

import pytest
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient

from app.api.v1 import auth as auth_module
from app.main import app
from app.models.user import User
from app.services.auth_service import AuthService


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


@pytest.fixture
def client() -> TestClient:
    repository = FakeUserRepository()
    service = AuthService(repository)

    async def override_get_auth_service() -> AuthService:
        return service

    async def override_get_current_user(request: Request) -> User:
        authorization = request.headers.get("authorization", "")
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Not authenticated")

        token = authorization.split(" ", 1)[1]
        try:
            payload = service.decode_access_token(token)
        except Exception as exc:
            raise HTTPException(status_code=401, detail="Invalid or expired token") from exc

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = await repository.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    app.dependency_overrides[auth_module.get_auth_service] = override_get_auth_service
    app.dependency_overrides[auth_module.get_current_user] = override_get_current_user
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
