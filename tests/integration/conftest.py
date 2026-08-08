"""Fixtures compartidos de integration auth (Task C.5).

Patrón alineado con tests/unit/test_simulate_profit_endpoint.py:
override de get_current_user en lugar de tokens JWT reales.
"""

from __future__ import annotations

from datetime import UTC
from typing import Any

import pytest
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient

from app.api.v1 import auth as auth_module
from app.api.v1.api_keys import get_api_key_service
from app.dependencies.auth import get_current_user
from app.main import app
from app.middleware.rate_limit_middleware import RateLimitMiddleware
from app.models.user import User
from app.services.api_key_service import ApiKeyService
from app.services.audit_service import AuditService
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

    async def update(self, user: User) -> User:
        self._users[user.email] = user
        return user


class FakeApiKeyRepository:
    def __init__(self) -> None:
        self._keys: dict[str, Any] = {}

    async def create(self, api_key: Any) -> Any:
        self._keys[api_key.id] = api_key
        return api_key

    async def get_by_id(self, key_id: str) -> Any | None:
        return self._keys.get(key_id)

    async def get_by_user_id(self, user_id: str) -> list[Any]:
        return [k for k in self._keys.values() if k.user_id == user_id]

    async def list_active_by_user_id(self, user_id: str) -> list[Any]:
        return [k for k in self._keys.values() if k.user_id == user_id and k.is_active]

    async def deactivate(self, key_id: str) -> None:
        if key_id in self._keys:
            self._keys[key_id].is_active = False

    async def update_last_used(self, key_id: str) -> None:
        from datetime import datetime
        if key_id in self._keys:
            self._keys[key_id].last_used_at = datetime.now(UTC)


class FakeAuditLogRepository:
    def __init__(self) -> None:
        self._logs: list[Any] = []

    async def create(self, log: Any) -> Any:
        self._logs.append(log)
        return log

    async def list_by_user_id(self, user_id: str, limit: int = 100) -> list[Any]:
        return [log for log in self._logs if log.user_id == user_id][:limit]

    async def list_by_action(self, action: str, limit: int = 100) -> list[Any]:
        return [log for log in self._logs if log.action == action][:limit]


class FakeRefreshTokenRepository:
    def __init__(self) -> None:
        self._tokens: dict[str, str] = {}

    async def create(self, refresh_token: Any) -> Any:
        self._tokens[refresh_token.token] = refresh_token.user_id
        return refresh_token

    async def get_by_token(self, token: str) -> Any | None:
        from app.models.refresh_token import RefreshToken
        if token not in self._tokens:
            return None
        return RefreshToken(token=token, user_id=self._tokens[token])

    async def revoke_by_token(self, token: str) -> None:
        if token in self._tokens:
            del self._tokens[token]

    async def revoke_all_by_user_id(self, user_id: str) -> None:
        self._tokens = {token: uid for token, uid in self._tokens.items() if uid != user_id}


user_repository = FakeUserRepository()
api_key_repository = FakeApiKeyRepository()
audit_log_repository = FakeAuditLogRepository()
refresh_token_repository = FakeRefreshTokenRepository()
auth_service = AuthService(user_repository)
api_key_service = ApiKeyService(api_key_repository)
audit_service = AuditService(audit_log_repository)
refresh_service = RefreshTokenService(refresh_token_repository)


def _reset_rate_limit_middleware() -> None:
    """Reset in-memory rate-limit buckets between tests.

    RateLimitMiddleware is a singleton registered on the app's middleware
    stack. Its local (fail-soft) counters persist across tests in the same
    process, so a test-heavy file can exhaust the login/register limits
    for later tests (F.1 uses Redis in prod, but tests fall back to memory).
    This walks the middleware stack and clears only the in-memory buckets.
    """
    current = getattr(app, "middleware_stack", None)
    for _ in range(10):
        if current is None:
            return
        if isinstance(current, RateLimitMiddleware):
            current._ip_limits.clear()
            current._endpoint_limits.clear()
            current._user_limits.clear()
            current._api_key_limits.clear()
            return
        current = getattr(current, "app", None)


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """Autouse: keep rate-limit state isolated per test."""
    yield
    _reset_rate_limit_middleware()


@pytest.fixture
def client() -> TestClient:
    # Clear state between tests
    user_repository._users.clear()
    api_key_repository._keys.clear()
    audit_log_repository._logs.clear()
    refresh_token_repository._tokens.clear()

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

    async def override_get_audit_service() -> AuditService:
        return audit_service

    async def override_get_refresh_token_service() -> RefreshTokenService:
        return refresh_service

    async def override_get_api_key_service() -> ApiKeyService:
        return api_key_service

    app.dependency_overrides[auth_module.get_auth_service] = override_get_auth_service
    app.dependency_overrides[auth_module.get_current_user] = override_get_current_user
    app.dependency_overrides[auth_module.get_audit_service] = override_get_audit_service
    app.dependency_overrides[auth_module.get_refresh_token_service] = override_get_refresh_token_service
    app.dependency_overrides[get_api_key_service] = override_get_api_key_service

    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def test_user() -> User:
    """Usuario de test con campos obligatorios del modelo User real.

    El __init__ de User rellena is_active, is_verified, role, created_at,
    updated_at e id si no se pasan.
    """
    return User(
        id="11111111-1111-1111-1111-111111111111",
        email="test@example.com",
        hashed_password="not-used-in-override",
    )


@pytest.fixture
def override_auth(test_user: User) -> User:
    """Override de get_current_user para endpoints autenticados.

    Hace yield del usuario y limpia el override al final.
    """
    async def _get_current_user() -> User:
        return test_user

    app.dependency_overrides[get_current_user] = _get_current_user
    yield test_user
    app.dependency_overrides.pop(get_current_user, None)
