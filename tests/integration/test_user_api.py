from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.v1 import auth as auth_module
from app.api.v1 import users as users_module
from app.dependencies.auth import get_current_user
from app.exceptions import UserAlreadyExistsError, UserNotFoundError
from app.main import app
from app.models.role import Role
from app.models.user import User


class StubUserService:
    def __init__(self) -> None:
        self._users: list[SimpleNamespace] = []
        self._next_id = 1

    async def create_user(self, *, email: str, hashed_password: str, full_name: str | None = None):
        if any(user.email == email for user in self._users):
            raise UserAlreadyExistsError("User already exists")

        user = SimpleNamespace(
            id=uuid4(),
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            is_active=True,
            is_verified=False,
            role=Role.USER,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self._users.append(user)
        return user

    async def list_users(self):
        return list(self._users)

    async def get_user(self, user_id: UUID):
        for user in self._users:
            if user.id == user_id:
                return user
        raise UserNotFoundError("User not found")

    async def update_user(self, user_id: UUID, **kwargs):
        for user in self._users:
            if user.id == user_id:
                for key, value in kwargs.items():
                    setattr(user, key, value)
                user.updated_at = datetime.now(UTC)
                return user
        raise UserNotFoundError("User not found")

    async def delete_user(self, user_id: UUID) -> None:
        if not any(user.id == user_id for user in self._users):
            raise UserNotFoundError("User not found")
        self._users = [user for user in self._users if user.id != user_id]


@pytest.fixture
def client() -> TestClient:
    service = StubUserService()
    audit_service = AsyncMock()

    async def override_get_user_service():
        return service

    async def override_get_current_user() -> User:
        return User(email="admin@example.com", hashed_password="secret", role=Role.ADMIN)

    app.dependency_overrides[users_module.get_user_service] = override_get_user_service
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[auth_module.get_audit_service] = lambda: audit_service
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_create_and_fetch_user(client: TestClient) -> None:
    response = client.post(
        "/api/v1/users/",
        json={"email": "new@example.com", "password": "secret-pass-123", "full_name": "New User"},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["email"] == "new@example.com"

    user_id = payload["id"]
    get_response = client.get(f"/api/v1/users/{user_id}")
    assert get_response.status_code == 200
    assert get_response.json()["email"] == "new@example.com"


def test_list_users(client: TestClient) -> None:
    response = client.get("/api/v1/users/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_update_user(client: TestClient) -> None:
    create_response = client.post(
        "/api/v1/users/",
        json={"email": "update@example.com", "password": "secret-pass-123"},
    )
    user_id = create_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/users/{user_id}",
        json={"full_name": "Updated Name"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["full_name"] == "Updated Name"


def test_delete_user(client: TestClient) -> None:
    create_response = client.post(
        "/api/v1/users/",
        json={"email": "delete@example.com", "password": "secret-pass-123"},
    )
    user_id = create_response.json()["id"]

    delete_response = client.delete(f"/api/v1/users/{user_id}")
    assert delete_response.status_code == 204

    get_response = client.get(f"/api/v1/users/{user_id}")
    assert get_response.status_code == 404
