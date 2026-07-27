from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.exceptions import AuthenticationError
from app.models.user import User
from app.repositories.api_key_repository import ApiKeyRepository
from app.repositories.user_repository import UserRepository
from app.services.api_key_service import ApiKeyService
from app.services.auth_service import AuthService
from app.services.user_service import UserService

# Paths that should not require authentication
PUBLIC_PATHS: set[str] = {
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/auth/register",
    "/auth/login",
    "/auth/refresh",
    "/auth/forgot-password",
    "/auth/reset-password",
}


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Unified authentication middleware supporting JWT Bearer and API Key auth.

    Checks for authentication in the following order:
    1. Authorization: Bearer <JWT> header
    2. X-API-Key: <api_key> header

    If neither is provided, the request proceeds without authentication
    (the dependency layer will enforce auth where needed).
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        # Skip authentication for public paths
        if request.url.path in PUBLIC_PATHS or request.url.path.startswith(("/auth/",)):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        api_key_header = request.headers.get("X-API-Key")

        if auth_header and auth_header.startswith("Bearer "):
            try:
                user = await self._authenticate_jwt(auth_header[7:])
                request.state.user = user
                request.state.auth_method = "jwt"
            except AuthenticationError:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid or expired token"},
                )
        elif api_key_header:
            try:
                user = await self._authenticate_api_key(api_key_header)
                request.state.user = user
                request.state.auth_method = "api_key"
            except AuthenticationError:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid API key"},
                )

        return await call_next(request)

    async def _authenticate_jwt(self, token: str) -> User:
        async with AsyncSessionLocal() as session:
            try:
                auth_service = AuthService(UserRepository(session))
                payload = auth_service.decode_access_token(token)
                user_id = payload.get("sub")
                if not user_id:
                    raise AuthenticationError("Invalid token")
                user_service = UserService(UserRepository(session))
                user = await user_service.get_user(user_id)
                if not user.is_active:
                    raise AuthenticationError("User is inactive")
                return user
            finally:
                await session.close()

    async def _authenticate_api_key(self, api_key: str) -> User:
        async with AsyncSessionLocal() as session:
            try:
                api_key_service = ApiKeyService(ApiKeyRepository(session))
                record = await api_key_service.validate_api_key(api_key)
                user_repo = UserRepository(session)
                user = await user_repo.get_by_id(record.user_id)
                if user is None or not user.is_active:
                    raise AuthenticationError("User not found or inactive")
                return user
            finally:
                await session.close()
