from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.audit_log import AuditLog
from app.services.audit_service import AuditService

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_repository() -> MagicMock:
    repo = AsyncMock()
    repo.create.return_value = AuditLog(
        id="test-log-id",
        user_id="user-1",
        action="test_action",
        resource="test_resource",
    )
    return repo


@pytest.fixture
def audit_service(mock_repository: MagicMock) -> AuditService:
    return AuditService(mock_repository)


class TestAuditService:
    async def test_log_creates_entry(
        self,
        audit_service: AuditService,
        mock_repository: MagicMock,
    ) -> None:
        """Test that log creates an audit entry."""
        result = await audit_service.log(
            action="test_action",
            resource="test_resource",
            user_id="user-1",
            details="Test details",
        )
        assert result.id == "test-log-id"
        assert result.action == "test_action"
        mock_repository.create.assert_called_once()

    async def test_log_login_success(
        self,
        audit_service: AuditService,
        mock_repository: MagicMock,
    ) -> None:
        """Test login success audit event."""
        await audit_service.log_login_success(
            user_id="user-1",
            ip_address="127.0.0.1",
        )
        mock_repository.create.assert_called_once()
        created_log = mock_repository.create.call_args[0][0]
        assert created_log.action == "login_success"
        assert created_log.resource == "auth"
        assert created_log.user_id == "user-1"
        assert created_log.ip_address == "127.0.0.1"

    async def test_log_login_failed(
        self,
        audit_service: AuditService,
        mock_repository: MagicMock,
    ) -> None:
        """Test login failed audit event."""
        await audit_service.log_login_failed(
            email="test@example.com",
            ip_address="192.168.1.1",
        )
        created_log = mock_repository.create.call_args[0][0]
        assert created_log.action == "login_failed"
        assert created_log.resource == "auth"
        assert "test@example.com" in created_log.details

    async def test_log_logout(
        self,
        audit_service: AuditService,
        mock_repository: MagicMock,
    ) -> None:
        """Test logout audit event."""
        await audit_service.log_logout(
            user_id="user-1",
            ip_address="10.0.0.1",
        )
        created_log = mock_repository.create.call_args[0][0]
        assert created_log.action == "logout"
        assert created_log.resource == "auth"
        assert created_log.user_id == "user-1"

    async def test_log_refresh_token(
        self,
        audit_service: AuditService,
        mock_repository: MagicMock,
    ) -> None:
        """Test refresh token audit event."""
        await audit_service.log_refresh_token(
            user_id="user-1",
        )
        created_log = mock_repository.create.call_args[0][0]
        assert created_log.action == "refresh_token"
        assert created_log.resource == "auth"

    async def test_log_api_key_created(
        self,
        audit_service: AuditService,
        mock_repository: MagicMock,
    ) -> None:
        """Test API key creation audit event."""
        await audit_service.log_api_key_created(
            user_id="user-1",
            api_key_id="key-1",
            name="My API Key",
        )
        created_log = mock_repository.create.call_args[0][0]
        assert created_log.action == "api_key_created"
        assert created_log.resource == "api_key"
        assert created_log.resource_id == "key-1"
        assert "My API Key" in created_log.details

    async def test_log_api_key_revoked(
        self,
        audit_service: AuditService,
        mock_repository: MagicMock,
    ) -> None:
        """Test API key revocation audit event."""
        await audit_service.log_api_key_revoked(
            user_id="user-1",
            api_key_id="key-1",
            name="Revoked Key",
        )
        created_log = mock_repository.create.call_args[0][0]
        assert created_log.action == "api_key_revoked"
        assert created_log.resource_id == "key-1"

    async def test_log_api_key_used(
        self,
        audit_service: AuditService,
        mock_repository: MagicMock,
    ) -> None:
        """Test API key usage audit event."""
        await audit_service.log_api_key_used(
            user_id="user-1",
            api_key_id="key-1",
        )
        created_log = mock_repository.create.call_args[0][0]
        assert created_log.action == "api_key_used"
        assert created_log.resource_id == "key-1"

    async def test_log_password_changed(
        self,
        audit_service: AuditService,
        mock_repository: MagicMock,
    ) -> None:
        """Test password change audit event."""
        await audit_service.log_password_changed(user_id="user-1")
        created_log = mock_repository.create.call_args[0][0]
        assert created_log.action == "password_changed"
        assert created_log.resource == "user"

    async def test_log_user_created(
        self,
        audit_service: AuditService,
        mock_repository: MagicMock,
    ) -> None:
        """Test user creation audit event."""
        await audit_service.log_user_created(user_id="new-user")
        created_log = mock_repository.create.call_args[0][0]
        assert created_log.action == "user_created"
        assert created_log.resource_id == "new-user"

    async def test_log_user_deleted(
        self,
        audit_service: AuditService,
        mock_repository: MagicMock,
    ) -> None:
        """Test user deletion audit event."""
        await audit_service.log_user_deleted(
            user_id="deleted-user",
            admin_user_id="admin-1",
        )
        created_log = mock_repository.create.call_args[0][0]
        assert created_log.action == "user_deleted"
        assert created_log.resource_id == "deleted-user"
        assert created_log.user_id == "admin-1"

    async def test_log_admin_access(
        self,
        audit_service: AuditService,
        mock_repository: MagicMock,
    ) -> None:
        """Test admin access audit event."""
        await audit_service.log_admin_access(
            user_id="admin-1",
            resource="admin_panel",
        )
        created_log = mock_repository.create.call_args[0][0]
        assert created_log.action == "admin_access"
        assert created_log.resource == "admin_panel"

    async def test_log_search_performed(
        self,
        audit_service: AuditService,
        mock_repository: MagicMock,
    ) -> None:
        """Test search performed audit event."""
        await audit_service.log_search_performed(
            user_id="user-1",
            search_id="search-1",
        )
        created_log = mock_repository.create.call_args[0][0]
        assert created_log.action == "search_performed"
        assert created_log.resource == "search"
        assert created_log.resource_id == "search-1"
