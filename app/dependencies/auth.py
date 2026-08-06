from __future__ import annotations

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.exceptions import AuthenticationError, AuthorizationError, UserNotFoundError
from app.models.role import Role
from app.models.user import User
from app.repositories.api_key_repository import ApiKeyRepository
from app.repositories.user_repository import UserRepository
from app.services.api_key_service import ApiKeyService
from app.services.auth_service import AuthService
from app.services.permission_service import PermissionService
from app.services.user_service import UserService

security = HTTPBearer(auto_error=False)

permission_service = PermissionService()


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """Get the current authenticated user.

    Supports both JWT Bearer token and API Key authentication.
    Checks request state first (set by AuthenticationMiddleware),
    then falls back to JWT Bearer token.
    """
    # Check if user was already authenticated by middleware
    if hasattr(request.state, "user") and request.state.user:
        return request.state.user

    # Fall back to JWT Bearer token authentication
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Not authenticated")

    auth_service = AuthService(UserRepository(session))
    payload = auth_service.decode_access_token(credentials.credentials)

    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Invalid token")

    user_service = UserService(UserRepository(session))
    try:
        user = await user_service.get_user(user_id)
        if not user.is_active:
            raise AuthenticationError("User is inactive")
        return user
    except UserNotFoundError as exc:
        raise AuthenticationError("Invalid token") from exc


def require_role(*roles: Role):
    async def role_dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise AuthorizationError("Insufficient permissions")
        return current_user

    return role_dependency


require_admin = require_role(Role.ADMIN)


def require_permission(permission: str):
    """Dependency factory that checks for a specific permission."""
    async def permission_dependency(current_user: User = Depends(get_current_user)) -> User:
        if not permission_service.can(current_user.role, permission):
            raise AuthorizationError("Insufficient permissions")
        return current_user

    return permission_dependency


require_search = require_permission("search")
require_manage_users = require_permission("manage_users")
require_manage_roles = require_permission("manage_roles")
require_manage_api_keys = require_permission("manage_api_keys")
require_manage_own_api_keys = require_permission("manage_own_api_keys")
require_view_admin = require_permission("view_admin")
require_view_audit_logs = require_permission("view_audit_logs")
