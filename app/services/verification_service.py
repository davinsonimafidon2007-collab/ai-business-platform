from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.exceptions import AuthenticationError, VerificationTokenExpiredError, VerificationTokenNotFoundError
from app.models.user import User
from app.models.verification_token import VerificationToken
from app.notifications.email_provider import EmailProvider
from app.repositories.user_repository import UserRepository
from app.repositories.verification_token_repository import VerificationTokenRepository

VERIFICATION_TOKEN_EXPIRE_HOURS = 24


def _hash_token(token: str) -> str:
    """Hash determinista del token (SHA-256). El raw solo viaja por email."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class VerificationService:
    def __init__(
        self,
        user_repository: UserRepository,
        token_repository: VerificationTokenRepository,
        email_provider: EmailProvider | None = None,
    ) -> None:
        self.user_repository = user_repository
        self.token_repository = token_repository
        self.email_provider = email_provider

    @staticmethod
    def _generate_token() -> str:
        """Genera un token de verificación seguro y aleatorio."""
        return secrets.token_urlsafe(48)

    async def request_verification(self, user: User) -> VerificationToken:
        """Crea un token de verificación para el usuario y envía el email.

        Args:
            user: Usuario que solicita la verificación.

        Returns:
            El VerificationToken creado.

        Raises:
            AuthenticationError: Si el usuario ya está verificado.
        """
        if user.is_verified:
            raise AuthenticationError("User is already verified")

        # Invalidar tokens anteriores no usados del mismo usuario
        existing_token = await self.token_repository.get_valid_by_user_id(str(user.id))
        if existing_token is not None:
            await self.token_repository.mark_as_used(existing_token)

        # Crear nuevo token
        raw_token = self._generate_token()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=VERIFICATION_TOKEN_EXPIRE_HOURS)

        token_record = VerificationToken(
            user_id=str(user.id),
            token=_hash_token(raw_token),
            expires_at=expires_at,
        )
        created_token = await self.token_repository.create(token_record)

        # Enviar email si hay provider configurado
        if self.email_provider is not None:
            await self._send_verification_email(user.email, raw_token)

        return created_token

    async def confirm_verification(self, raw_token: str) -> User:
        """Confirma la verificación del usuario mediante un token.

        Args:
            raw_token: Token de verificación enviado al usuario.

        Returns:
            El usuario actualizado con is_verified=True.

        Raises:
            VerificationTokenNotFoundError: Si el token no existe.
            VerificationTokenExpiredError: Si el token ha expirado.
            AuthenticationError: Si el token ya fue usado.
        """
        token_record = await self.token_repository.get_by_token(_hash_token(raw_token))
        if token_record is None:
            raise VerificationTokenNotFoundError("Verification token not found")

        if token_record.is_used:
            raise VerificationTokenExpiredError("Verification token has already been used")

        if token_record.expires_at is None or token_record.expires_at < datetime.now(timezone.utc):
            raise VerificationTokenExpiredError("Verification token has expired")

        # Marcar token como usado
        await self.token_repository.mark_as_used(token_record)

        # Actualizar usuario
        user = await self.user_repository.get_by_id(token_record.user_id)
        if user is None:
            raise VerificationTokenNotFoundError("User associated with token not found")

        user.is_verified = True
        return await self.user_repository.update(user)

    async def _send_verification_email(self, to_email: str, token: str) -> None:
        """Envía el email de verificación al usuario."""
        verify_link = f"{settings.app_url or 'http://localhost:3000'}/auth/verify?token={token}"
        body_html = (
            f"<h1>Verify your email</h1>"
            f"<p>Click the link below to verify your email address:</p>"
            f"<p><a href='{verify_link}'>{verify_link}</a></p>"
            f"<p>This link expires in {VERIFICATION_TOKEN_EXPIRE_HOURS} hours.</p>"
            f"<p>If you did not create an account, please ignore this email.</p>"
        )
        body_text = (
            f"Verify your email\n\n"
            f"Click the link below to verify your email address:\n\n"
            f"{verify_link}\n\n"
            f"This link expires in {VERIFICATION_TOKEN_EXPIRE_HOURS} hours.\n\n"
            f"If you did not create an account, please ignore this email."
        )

        await self.email_provider.send_email(
            to_email=to_email,
            subject="Verify your email address",
            body_html=body_html,
            body_text=body_text,
        )