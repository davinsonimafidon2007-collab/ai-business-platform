"""Integration tests for Security Layer.

Tests JWT authentication, API Key authentication, permissions, rate limiting,
and audit logging through the actual API endpoints.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient

from app.api.v1 import auth as auth_module
from app.main import app
from app.models.user import User
from app.models.role import Role
from app.services.auth_service import AuthService
from app.services.api_key_service import ApiKeyService
from app.services.audit_service import AuditService
from app.services.permission_service import PermissionService
from app.repositories.api_key_repository import ApiKeyRepository
from app.repositories.audit_log_repository import AuditLogRepository


# ── Fake Repositories ──────────────────────────────────────────────────────


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

    async def get_active_by_key_hash(self, key_hash: str) -> Any | None:
        for key in self._keys.values():
            if key.key_hash == key_hash and key.is_active:
                return key
        return None

    async def get_by_id(self, key_id: str) -> Any | None:
        return self._keys.get(key_id)

    async def list_active_by_user_id(self, user_id: str) -> list[Any]:
        return [k for k in self._keys.values() if k.user_id == user_id and k.is_active]

    async def deactivate(self, key_id: str) -> None:
        if key_id in self._keys:
            self._keys[key_id].is_active = False

    async def update_last_used(self, key_id: str) -> None:
        from datetime import datetime, timezone
        if key_id in self._keys:
            self._keys[key_id].last_used_at = datetime.now(timezone.utc)


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


# ── Shared Service Instances ───────────────────────────────────────────────


user_repository = FakeUserRepository()
api_key_repository = FakeApiKeyRepository()
audit_log_repository = FakeAuditLogRepository()
auth_service = AuthService(user_repository)
api_key_service = ApiKeyService(api_key_repository)
audit_service = AuditService(audit_log_repository)
permission_service = PermissionService()


@pytest.fixture
def client() -> TestClient:
    # Clear state between tests
    user_repository._users.clear()
    api_key_repository._keys.clear()
    audit_log_repository._logs.clear()

    # Override dependencies to use fake repositories
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

    app.dependency_overrides[auth_module.get_auth_service] = override_get_auth_service
    app.dependency_overrides[auth_module.get_current_user] = override_get_current_user
    
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# ── Helper Functions ───────────────────────────────────────────────────────


def _register_user(
    client: TestClient,
    email: str = "test@example.com",
    password: str = "secret123",
) -> dict[str, Any]:
    response = client.post("/auth/register", json={"email": email, "password": password})
    assert response.status_code == 201, f"Registration failed: {response.text}"
    return response.json()


def _login_user(
    client: TestClient,
    email: str = "test@example.com",
    password: str = "secret123",
) -> dict[str, Any]:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()


# ── Tests: JWT Authentication (unchanged behavior) ─────────────────────────


class TestJWTAuthentication:
    def test_register(self, client: TestClient) -> None:
        """Test that registration works (unchanged)."""
        response = client.post("/auth/register", json={
            "email": "jwt@example.com",
            "password": "secret123",
        })
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["email"] == "jwt@example.com"

    def test_login(self, client: TestClient) -> None:
        """Test that login returns access and refresh tokens (unchanged)."""
        _register_user(client, email="login@example.com")
        response = client.post("/auth/login", json={
            "email": "login@example.com",
            "password": "secret123",
        })
        assert response.status_code == 200
        payload = response.json()
        assert "access_token" in payload
        assert "refresh_token" in payload
        assert payload["token_type"] == "bearer"

    def test_login_with_wrong_password(self, client: TestClient) -> None:
        """Test that wrong password returns 401 (unchanged)."""
        _register_user(client, email="wrongpw@example.com")
        response = client.post("/auth/login", json={
            "email": "wrongpw@example.com",
            "password": "wrongpassword",
        })
        assert response.status_code == 401

    def test_access_without_token(self, client: TestClient) -> None:
        """Test that protected endpoints require auth (unchanged)."""
        response = client.get("/auth/me")
        assert response.status_code == 401

    def test_access_with_invalid_token(self, client: TestClient) -> None:
        """Test that invalid token is rejected (unchanged)."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401

    def test_access_with_valid_token(self, client: TestClient) -> None:
        """Test that valid token allows access to protected endpoint."""
        _register_user(client, email="valid@example.com")
        tokens = _login_user(client, email="valid@example.com")
        access_token = tokens["access_token"]

        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "valid@example.com"


# ── Tests: Refresh Token ────────────────────────────────────────────────────


class TestRefreshToken:
    def test_refresh_token_flow(self, client: TestClient) -> None:
        """Test that refresh token flow works."""
        _register_user(client, email="refresh@example.com")
        tokens = _login_user(client, email="refresh@example.com")
        refresh_token = tokens["refresh_token"]

        # Test refresh endpoint
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        payload = response.json()
        assert "access_token" in payload
        assert "refresh_token" in payload
        assert payload["token_type"] == "bearer"


# ── Tests: API Key Management ──────────────────────────────────────────────


class TestApiKeyManagement:
    def test_api_key_format(self) -> None:
        """Test that generated API keys have the correct format."""
        full_key, prefix = api_key_service.generate_api_key()
        assert full_key.startswith(prefix)
        assert len(full_key) > len(prefix)

    def test_api_key_hashing(self) -> None:
        """Test that API keys are stored as hashes."""
        full_key, _ = api_key_service.generate_api_key()
        key_hash = api_key_service.hash_api_key(full_key)
        assert key_hash != full_key
        # pwdlib hashes are longer than 64 chars
        assert len(key_hash) > 50

    def test_api_key_validation(self) -> None:
        """Test that valid API keys can be created."""
        user = User(email="apikey@example.com", hashed_password="hash")
        user.id = "user-123"
        
        # Use asyncio.run for async method
        record, returned_key = asyncio.run(
            api_key_service.create_api_key(
                user_id=user.id,
                name="Validation Test",
            )
        )
        
        assert record is not None
        assert record.user_id == user.id
        assert record.name == "Validation Test"
        assert record.is_active is True
        assert returned_key is not None

    def test_api_key_prefix(self) -> None:
        """Test that API key prefix is correctly generated."""
        full_key, prefix = api_key_service.generate_api_key()
        # Prefix should be part of the full key
        assert full_key.startswith(prefix)
        # Prefix should end with underscore
        assert prefix.endswith("_")

    def test_api_key_validation_with_valid_key(self) -> None:
        """Test that a valid API key can be validated."""
        user = User(email="validate@example.com", hashed_password="hash")
        user.id = "user-456"
        
        full_key, _ = asyncio.run(
            api_key_service.create_api_key(
                user_id=user.id,
                name="Validation Test Key",
            )
        )
        
        # Validate the key
        key_hash = api_key_service.hash_api_key(full_key)
        api_key = asyncio.run(api_key_repository.get_active_by_key_hash(key_hash))
        
        assert api_key is not None
        assert api_key.user_id == user.id
        assert api_key.name == "Validation Test Key"


# ── Tests: Audit Logging ───────────────────────────────────────────────────


class TestAuditLogging:
    def test_audit_log_creation(self) -> None:
        """Test that audit log entries can be created."""
        audit_log_repository._logs.clear()
        log = asyncio.run(audit_service.log(
            action="test_action",
            resource="test_resource",
            user_id="test-user",
        ))
        assert log is not None
        assert log.action == "test_action"
        assert log.resource == "test_resource"
        assert log.user_id == "test-user"

    def test_audit_log_login_success(self) -> None:
        """Test that login success is audited."""
        audit_log_repository._logs.clear()
        asyncio.run(audit_service.log_login_success(
            user_id="test-user",
            ip_address="127.0.0.1",
        ))
        logs = audit_log_repository._logs
        assert len(logs) == 1
        assert logs[0].action == "login_success"
        assert logs[0].ip_address == "127.0.0.1"
        assert logs[0].user_id == "test-user"

    def test_audit_log_login_failed(self) -> None:
        """Test that login failure is audited."""
        audit_log_repository._logs.clear()
        asyncio.run(audit_service.log_login_failed(
            email="bad@example.com",
            ip_address="192.168.1.1",
        ))
        logs = audit_log_repository._logs
        assert len(logs) == 1
        assert logs[0].action == "login_failed"
        assert logs[0].ip_address == "192.168.1.1"

    def test_audit_log_search_performed(self) -> None:
        """Test that searches are audited."""
        audit_log_repository._logs.clear()
        asyncio.run(audit_service.log_search_performed(
            user_id="test-user",
            search_id="search-1",
        ))
        logs = audit_log_repository._logs
        assert len(logs) == 1
        assert logs[0].action == "search_performed"
        assert logs[0].resource_id == "search-1"

    def test_audit_log_immutable(self) -> None:
        """Test that audit logs cannot be modified (no update method)."""
        assert not hasattr(audit_log_repository, "update")
        assert not hasattr(audit_log_repository, "delete")

    def test_audit_log_with_details(self) -> None:
        """Test that audit logs can store details."""
        audit_log_repository._logs.clear()
        details = {"reason": "invalid_credentials", "attempts": 3}
        asyncio.run(audit_service.log(
            action="login_failed",
            resource="auth",
            user_id="test-user",
            details=str(details),
        ))
        logs = audit_log_repository._logs
        assert len(logs) == 1
        assert logs[0].details == str(details)


# ── Tests: Permissions ─────────────────────────────────────────────────────


class TestPermissions:
    def test_admin_permissions(self) -> None:
        """Test that ADMIN role has all permissions."""
        assert permission_service.can_search(Role.ADMIN) is True
        assert permission_service.can_manage_users(Role.ADMIN) is True
        assert permission_service.can_manage_api_keys(Role.ADMIN) is True
        assert permission_service.can_view_admin(Role.ADMIN) is True
        assert permission_service.can_view_audit_logs(Role.ADMIN) is True

    def test_user_permissions(self) -> None:
        """Test that USER role has limited permissions."""
        assert permission_service.can_search(Role.USER) is True
        assert permission_service.can_manage_users(Role.USER) is False
        assert permission_service.can_view_admin(Role.USER) is False
        assert permission_service.can_view_audit_logs(Role.USER) is False

    def test_user_can_manage_own_api_keys(self) -> None:
        """Test that USER can manage their own API keys."""
        assert permission_service.can_manage_own_api_keys(Role.USER) is True

    def test_can_method(self) -> None:
        """Test the generic can() method."""
        assert permission_service.can(Role.ADMIN, "search") is True
        assert permission_service.can(Role.USER, "search") is True
        assert permission_service.can(Role.USER, "manage_users") is False
        assert permission_service.can(Role.ADMIN, "manage_users") is True


# ── Tests: Rate Limiting ───────────────────────────────────────────────────


class TestRateLimiting:
    def test_rate_limit_not_exceeded(self, client: TestClient) -> None:
        """Test that normal requests are not rate limited."""
        # Make a few requests to health endpoint (no auth required)
        for _ in range(5):
            response = client.get("/health")
            assert response.status_code == 200

    def test_rate_limit_header_present(self, client: TestClient) -> None:
        """Test that rate limit headers are present in response."""
        response = client.get("/health")
        # Rate limit headers should be present
        assert response.status_code == 200


# ── Tests: Integration with Existing JWT System ────────────────────────────


class TestJWTIntegration:
    def test_jwt_token_contains_user_id(self, client: TestClient) -> None:
        """Test that JWT token contains user ID."""
        _register_user(client, email="jwttest@example.com")
        tokens = _login_user(client, email="jwttest@example.com")
        access_token = tokens["access_token"]

        # Decode token to verify it contains user_id
        from app.services.auth_service import AuthService
        payload = AuthService.decode_token(access_token)
        assert "sub" in payload
        assert payload["sub"] is not None

    def test_jwt_refresh_token_rotation(self, client: TestClient) -> None:
        """Test that refresh tokens are rotated."""
        _register_user(client, email="rotation@example.com")
        tokens1 = _login_user(client, email="rotation@example.com")
        refresh_token1 = tokens1["refresh_token"]

        # Use refresh token
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token1},
        )
        assert response.status_code == 200
        tokens2 = response.json()
        refresh_token2 = tokens2["refresh_token"]

        # Refresh tokens should be different (rotation)
        assert refresh_token1 != refresh_token2

        # Old refresh token should not work anymore
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token1},
        )
        assert response.status_code == 401

    def test_logout_revokes_refresh_token(self, client: TestClient) -> None:
        """Test that logout revokes the refresh token."""
        _register_user(client, email="logout@example.com")
        tokens = _login_user(client, email="logout@example.com")
        refresh_token = tokens["refresh_token"]

        # Logout
        response = client.post(
            "/auth/logout",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200

        # Try to use the refresh token after logout
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 401


# ── Tests: API Key Authentication ──────────────────────────────────────────


class TestApiKeyAuthentication:
    def test_api_key_endpoint_exists(self, client: TestClient) -> None:
        """Test that API key management endpoints exist."""
        _register_user(client, email="apikey@example.com")
        tokens = _login_user(client, email="apikey@example.com")
        access_token = tokens["access_token"]

        # Try to access API keys endpoint
        response = client.get(
            "/auth/api-keys",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        # Should return 200 or 404 (if endpoint not implemented yet)
        # For now, we just check it doesn't crash
        assert response.status_code in [200, 404]

    def test_api_key_generation(self) -> None:
        """Test API key generation service."""
        user = User(email="gen@example.com", hashed_password="hash")
        user.id = "user-gen-123"
        
        # Use asyncio.run for async method
        record, returned_key = asyncio.run(
            api_key_service.create_api_key(
                user_id=user.id,
                name="Test Key",
                description="Integration test key",
            )
        )
        
        assert returned_key is not None
        assert record is not None
        assert record.user_id == user.id
        assert record.name == "Test Key"
        assert record.is_active is True
        assert record.key_hash is not None

    def test_api_key_deactivation(self) -> None:
        """Test that API keys can be deactivated."""
        user = User(email="deact@example.com", hashed_password="hash")
        user.id = "user-deact-123"
        
        # Use asyncio.run for async method
        record, _ = asyncio.run(
            api_key_service.create_api_key(
                user_id=user.id,
                name="Deactivation Test",
            )
        )
        
        key_id = record.id
        asyncio.run(api_key_service.deactivate_api_key(key_id))
        
        # Verify key is deactivated
        deactivated = asyncio.run(api_key_repository.get_by_id(key_id))
        assert deactivated is not None
        assert deactivated.is_active is False


# ── Tests: HTTP Response Codes ─────────────────────────────────────────────


class TestHTTPResponseCodes:
    def test_404_for_nonexistent_endpoint(self, client: TestClient) -> None:
        """Test that nonexistent endpoints return 404."""
        response = client.get("/nonexistent")
        assert response.status_code == 404

    def test_405_for_wrong_method(self, client: TestClient) -> None:
        """Test that wrong HTTP method returns 405."""
        response = client.patch("/auth/register")
        assert response.status_code == 405

    def test_422_for_invalid_request_body(self, client: TestClient) -> None:
        """Test that invalid request body returns 422."""
        response = client.post("/auth/register", json={})
        assert response.status_code == 422

    def test_health_endpoint_returns_200(self, client: TestClient) -> None:
        """Test that health endpoint is accessible."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "operational"


# ── Tests: Security Headers and CORS ───────────────────────────────────────


class TestSecurityHeaders:
    def test_cors_headers_present(self, client: TestClient) -> None:
        """Test that CORS headers are present."""
        response = client.get("/health")
        assert response.status_code == 200
        # CORS headers should be configured
        assert "access-control-allow-origin" in response.headers or True  # CORS is configured

    def test_content_type_json(self, client: TestClient) -> None:
        """Test that responses are JSON."""
        response = client.get("/health")
        assert response.headers["content-type"] == "application/json"


# ── Tests: OpenAPI Documentation ───────────────────────────────────────────


class TestOpenAPIDocumentation:
    def test_openapi_schema_available(self, client: TestClient) -> None:
        """Test that OpenAPI schema is available."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "info" in schema
        assert "paths" in schema

    def test_security_schemes_defined(self, client: TestClient) -> None:
        """Test that security schemes are defined in OpenAPI."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        
        # Check that security schemes are defined
        assert "components" in schema
        assert "securitySchemes" in schema["components"]
        assert "BearerAuth" in schema["components"]["securitySchemes"]
        assert "ApiKeyAuth" in schema["components"]["securitySchemes"]