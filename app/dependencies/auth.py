from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.exceptions import AuthenticationError, UserNotFoundError
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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    auth_service = AuthService(UserRepository(session))
    try:
        payload = auth_service.decode_access_token(credentials.credentials)
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_service = UserService(UserRepository(session))
    try:
        return await user_service.get_user(user_id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
