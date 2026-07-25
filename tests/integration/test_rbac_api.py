from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.api.v1 import users as users_module
from app.core.config import settings
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.role import Role
from app.models.user import User


class StubUserService:
    def __init__(self) -> None:
        self.user = SimpleNamespace(
            id=uuid4(),
            email="member@example.com",
            hashed_password="secret",
            full_name=None,
            is_active=True,
            is_verified=False,
            role=Role.USER,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    async def list_users(self) -> list[SimpleNamespace]:
        return [self.user]

    async def get_user(self, user_id: object) -> SimpleNamespace:
        return self.user

    async def delete_user(self, user_id: object) -> None:
        return None


@pytest.fixture
def client() -> TestClient:
    service = StubUserService()
    current_user = User(email="member@example.com", hashed_password="secret", role=Role.USER)

    async def override_get_user_service() -> StubUserService:
        return service

    async def override_get_current_user() -> User:
        return current_user

    app.dependency_overrides[users_module.get_user_service] = override_get_user_service
    app.dependency_overrides[get_current_user] = override_get_current_user
    try:
        test_client = TestClient(app, raise_server_exceptions=False)
        test_client.current_user = current_user  # type: ignore[attr-defined]
        yield test_client
    finally:
        app.dependency_overrides.clear()


def test_admin_access_is_allowed(client: TestClient) -> None:
    client.current_user.role = Role.ADMIN  # type: ignore[attr-defined]

    response = client.get("/users/")

    assert response.status_code == 200


def test_user_access_is_allowed(client: TestClient) -> None:
    response = client.get(f"/users/{uuid4()}")

    assert response.status_code == 200


def test_user_is_forbidden_from_admin_endpoint(client: TestClient) -> None:
    response = client.get("/users/")

    assert response.status_code == 403


def test_authenticated_user_without_permission_is_forbidden(client: TestClient) -> None:
    response = client.delete(f"/users/{uuid4()}")

    assert response.status_code == 403


@pytest.fixture
def unauthenticated_client() -> TestClient:
    service = StubUserService()

    async def override_get_user_service() -> StubUserService:
        return service

    app.dependency_overrides[users_module.get_user_service] = override_get_user_service
    try:
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        app.dependency_overrides.clear()


def test_missing_jwt_returns_401(unauthenticated_client: TestClient) -> None:
    response = unauthenticated_client.get(f"/users/{uuid4()}")

    assert response.status_code == 401


def test_invalid_jwt_returns_401(unauthenticated_client: TestClient) -> None:
    response = unauthenticated_client.get(
        f"/users/{uuid4()}",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


def test_expired_jwt_returns_401(unauthenticated_client: TestClient) -> None:
    token = jwt.encode(
        {"sub": str(uuid4()), "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    response = unauthenticated_client.get(
        f"/users/{uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
