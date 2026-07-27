from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.models.audit_log import AuditLog
from app.repositories.audit_log_repository import AuditLogRepository


class AuditService:
    """Service for logging immutable audit events."""

    def __init__(self, repository: AuditLogRepository) -> None:
        self.repository = repository

    async def log(
        self,
        *,
        action: str,
        resource: str,
        resource_id: str | None = None,
        user_id: str | None = None,
        details: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        """Create an immutable audit log entry."""
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.now(timezone.utc),
        )
        return await self.repository.create(audit_log)

    # ── Convenience methods for common audit events ──────────────────────

    async def log_login_success(
        self,
        user_id: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        return await self.log(
            action="login_success",
            resource="auth",
            user_id=user_id,
            details="User logged in successfully",
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def log_login_failed(
        self,
        *,
        email: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        return await self.log(
            action="login_failed",
            resource="auth",
            details=f"Failed login attempt for email: {email}",
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def log_logout(
        self,
        user_id: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        return await self.log(
            action="logout",
            resource="auth",
            user_id=user_id,
            details="User logged out",
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def log_refresh_token(
        self,
        user_id: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        return await self.log(
            action="refresh_token",
            resource="auth",
            user_id=user_id,
            details="Access token refreshed",
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def log_api_key_created(
        self,
        user_id: str,
        api_key_id: str,
        *,
        name: str,
        ip_address: str | None = None,
    ) -> AuditLog:
        return await self.log(
            action="api_key_created",
            resource="api_key",
            resource_id=api_key_id,
            user_id=user_id,
            details=f"API key '{name}' created",
            ip_address=ip_address,
        )

    async def log_api_key_revoked(
        self,
        user_id: str,
        api_key_id: str,
        *,
        name: str,
        ip_address: str | None = None,
    ) -> AuditLog:
        return await self.log(
            action="api_key_revoked",
            resource="api_key",
            resource_id=api_key_id,
            user_id=user_id,
            details=f"API key '{name}' revoked",
            ip_address=ip_address,
        )

    async def log_api_key_used(
        self,
        user_id: str,
        api_key_id: str,
        *,
        ip_address: str | None = None,
    ) -> AuditLog:
        return await self.log(
            action="api_key_used",
            resource="api_key",
            resource_id=api_key_id,
            user_id=user_id,
            details="API key used for authentication",
            ip_address=ip_address,
        )

    async def log_password_changed(
        self,
        user_id: str,
        *,
        ip_address: str | None = None,
    ) -> AuditLog:
        return await self.log(
            action="password_changed",
            resource="user",
            resource_id=user_id,
            user_id=user_id,
            details="Password changed",
            ip_address=ip_address,
        )

    async def log_user_created(
        self,
        user_id: str,
        *,
        admin_user_id: str | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        return await self.log(
            action="user_created",
            resource="user",
            resource_id=user_id,
            user_id=admin_user_id or user_id,
            details=f"User {user_id} created",
            ip_address=ip_address,
        )

    async def log_user_deleted(
        self,
        user_id: str,
        *,
        admin_user_id: str,
        ip_address: str | None = None,
    ) -> AuditLog:
        return await self.log(
            action="user_deleted",
            resource="user",
            resource_id=user_id,
            user_id=admin_user_id,
            details=f"User {user_id} deleted",
            ip_address=ip_address,
        )

    async def log_admin_access(
        self,
        user_id: str,
        *,
        resource: str,
        ip_address: str | None = None,
    ) -> AuditLog:
        return await self.log(
            action="admin_access",
            resource=resource,
            user_id=user_id,
            details=f"Admin accessed {resource}",
            ip_address=ip_address,
        )

    async def log_search_performed(
        self,
        user_id: str,
        *,
        search_id: str,
        ip_address: str | None = None,
    ) -> AuditLog:
        return await self.log(
            action="search_performed",
            resource="search",
            resource_id=search_id,
            user_id=user_id,
            details="Search performed",
            ip_address=ip_address,
        )
