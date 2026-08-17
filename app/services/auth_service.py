from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

from app.core.config import settings
from app.core.firebase import verify_google_id_token
from app.exceptions import AuthenticationError, InvalidCredentialsError, UserAlreadyExistsError
from app.models.user import User
from app.repositories.user_repository import UserRepository

password_hasher = PasswordHash.recommended()


class AuthService:
    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    async def register_user(self, *, email: str, password: str) -> User:
        existing_user = await self.repository.get_by_email(email)
        if existing_user is not None:
            raise UserAlreadyExistsError(f"User with email '{email}' already exists")

        hashed_password = password_hasher.hash(password)
        user = User(email=email, hashed_password=hashed_password)
        return await self.repository.create(user)

    async def authenticate_user(self, *, email: str, password: str) -> User:
        user = await self.repository.get_by_email(email)
        if user is None:
            raise InvalidCredentialsError("Invalid email or password")

        try:
            is_valid_password = password_hasher.verify(password, user.hashed_password)
        except UnknownHashError as exc:
            raise InvalidCredentialsError("Invalid email or password") from exc

        if not is_valid_password:
            raise InvalidCredentialsError("Invalid email or password")

        if not user.is_active:
            raise AuthenticationError("User is inactive")

        return user

    async def authenticate_with_google(self, *, id_token: str) -> User:
        """Verify a Firebase ID token and return the corresponding user.

        Uses the Firebase Admin SDK to verify the token.
        Creates the user if it does not exist yet.
        """
        try:
            token_info = await verify_google_id_token(id_token)
        except ValueError as exc:
            raise AuthenticationError(str(exc)) from exc

        email = token_info.get("email")
        if not email:
            raise AuthenticationError("Invalid Google token: no email")

        user = await self.repository.get_by_email(email)
        if user is None:
            user = User(
                email=email,
                hashed_password=password_hasher.hash(secrets.token_urlsafe(32)),
                full_name=token_info.get("name"),
                is_verified=token_info.get("email_verified", False),
            )
            user = await self.repository.create(user)

        if not user.is_active:
            raise AuthenticationError("User is inactive")

        return user

    def create_access_token(self, *, user_id: str | Any) -> str:
        expire_at = datetime.now(UTC) + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )
        # RFC 7519: exp debe ser NumericDate (segundos Unix), no datetime
        payload = {
            "sub": str(user_id),
            "exp": int(expire_at.timestamp()),
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    def decode_access_token(self, token: str) -> dict[str, Any]:
        """Decodifica un JWT intentando la clave actual y las previas.

        TASK-015: si ``jwt_secret_key`` se ha rotado, los tokens firmados con
        ``jwt_previous_secrets`` siguen siendo válidos hasta su expiración.
        """
        keys = [settings.jwt_secret_key, *settings.jwt_previous_secrets]
        last_error: JWTError | None = None
        for key in keys:
            if not key:
                continue
            try:
                return jwt.decode(
                    token, key, algorithms=[settings.jwt_algorithm]
                )
            except JWTError as exc:
                last_error = exc
        raise AuthenticationError("Invalid or expired token") from last_error
