from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from app.core.config import settings
from app.exceptions import AuthenticationError
from app.models.refresh_token import RefreshToken
from app.repositories.refresh_token_repository import RefreshTokenRepository


def _hash_token(token: str) -> str:
    """Hash determinista del refresh token para no guardarlo en claro en BBDD.

    SHA-256 simple (sin HMAC) es suficiente aquí porque el propio token ya es
    un JWT de alta entropía firmado con JWT_SECRET_KEY — no hace falta un
    secreto adicional, solo evitar que quede legible tal cual en la tabla.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class RefreshTokenService:
    def __init__(self, repository: RefreshTokenRepository) -> None:
        self.repository = repository

    def create_refresh_token(self, *, user_id: str | Any) -> str:
        expire_at = datetime.now(UTC) + timedelta(
            minutes=settings.jwt_refresh_token_expire_minutes
        )
        payload = {
            "sub": str(user_id),
            "exp": int(expire_at.timestamp()),
            "type": "refresh",
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    def decode_refresh_token(self, token: str) -> dict[str, Any]:
        try:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            if payload.get("type") != "refresh":
                raise AuthenticationError("Invalid token type")
            return payload
        except JWTError as exc:
            raise AuthenticationError("Invalid or expired refresh token") from exc

    async def create_refresh_token_record(self, *, user_id: str, token: str) -> RefreshToken:
        expires_at = datetime.now(UTC) + timedelta(minutes=settings.jwt_refresh_token_expire_minutes)
        refresh_token = RefreshToken(
            token=_hash_token(token),
            user_id=user_id,
            expires_at=expires_at,
        )
        return await self.repository.create(refresh_token)

    async def validate_refresh_token(self, token: str) -> RefreshToken:
        # Valida firma/exp/type y lanza AuthenticationError si no cuadra.
        # El payload no se usa aquí: la fuente de verdad es la fila en DB.
        self.decode_refresh_token(token)
        refresh_token = await self.repository.get_by_token(_hash_token(token))
        
        if refresh_token is None:
            raise AuthenticationError("Refresh token not found")
        
        if refresh_token.is_revoked:
            raise AuthenticationError("Refresh token has been revoked")

        if refresh_token.expires_at is None or refresh_token.expires_at < datetime.now(UTC):
            raise AuthenticationError("Refresh token has expired")
        
        return refresh_token

    async def revoke_refresh_token(self, token: str) -> None:
        await self.repository.revoke_by_token(_hash_token(token))

    async def revoke_all_user_tokens(self, user_id: str) -> None:
        await self.repository.revoke_all_by_user_id(user_id)