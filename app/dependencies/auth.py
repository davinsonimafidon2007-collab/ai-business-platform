from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.exceptions import AuthenticationError, AuthorizationError, UserNotFoundError
from app.models.role import Role
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.user_service import UserService

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Not authenticated")

    auth_service = AuthService(UserRepository(session))
    payload = auth_service.decode_access_token(credentials.credentials)

    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Invalid token")

    user_service = UserService(UserRepository(session))
    try:
        return await user_service.get_user(user_id)
    except UserNotFoundError as exc:
        raise AuthenticationError("Invalid token") from exc


def require_role(*roles: Role):
    async def role_dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise AuthorizationError("Insufficient permissions")
        return current_user

    return role_dependency


require_admin = require_role(Role.ADMIN)
