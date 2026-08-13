from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from app.core.config import settings
from app.exceptions import (
    PasswordResetError,
    PasswordResetTokenExpiredError,
    PasswordResetTokenNotFoundError,
)
from app.models.password_reset_token import PasswordResetToken
from app.notifications.email_provider import EmailProvider
from app.repositories.password_reset_token_repository import PasswordResetTokenRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import password_hasher


def _hash_token(token: str) -> str:
    """Hash determinista del token (SHA-256). El raw solo viaja por email."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class PasswordResetService:
    def __init__(
        self,
        user_repository: UserRepository,
        token_repository: PasswordResetTokenRepository,
        email_provider: EmailProvider | None = None,
        refresh_token_repository: RefreshTokenRepository | None = None,
    ) -> None:
        self.user_repository = user_repository
        self.token_repository = token_repository
        self.email_provider = email_provider
        self.refresh_token_repository = refresh_token_repository

    @staticmethod
    def _generate_token() -> str:
        """Genera un token de reset seguro y aleatorio."""
        return secrets.token_urlsafe(48)

    async def request_password_reset(self, email: str) -> None:
        """Solicita un reset de contraseña para el email dado.

        Por seguridad, siempre responde con el mismo mensaje
        independientemente de si el email existe o no.

        Args:
            email: Email del usuario que solicita el reset.
        """
        user = await self.user_repository.get_by_email(email)
        if user is None:
            # No revelar si el email existe o no
            return

        # Invalidar tokens anteriores no usados del mismo usuario
        existing_token = await self.token_repository.get_valid_by_user_id(str(user.id))
        if existing_token is not None:
            await self.token_repository.mark_as_used(existing_token)

        # Crear nuevo token
        raw_token = self._generate_token()
        expires_at = datetime.now(UTC) + timedelta(
            hours=settings.password_reset_token_expire_hours
        )

        token_record = PasswordResetToken(
            user_id=str(user.id),
            token=_hash_token(raw_token),
            expires_at=expires_at,
        )
        await self.token_repository.create(token_record)

        # Enviar email si hay provider configurado
        if self.email_provider is not None:
            await self._send_reset_email(user.email, raw_token)

    async def reset_password(self, raw_token: str, new_password: str) -> str:
        """Resetea la contraseña del usuario usando un token válido.

        Args:
            raw_token: Token de reset enviado al usuario.
            new_password: Nueva contraseña del usuario.

        Returns:
            El ID del usuario cuya contraseña fue reseteada.

        Raises:
            PasswordResetTokenNotFoundError: Si el token no existe.
            PasswordResetTokenExpiredError: Si el token ha expirado o ya fue usado.
            PasswordResetError: Si el usuario asociado no se encuentra.
        """
        token_record = await self.token_repository.get_by_token(_hash_token(raw_token))
        if token_record is None:
            raise PasswordResetTokenNotFoundError("Password reset token not found")

        if token_record.is_used:
            raise PasswordResetTokenExpiredError("Password reset token has already been used")

        if token_record.expires_at is None or token_record.expires_at < datetime.now(UTC):
            raise PasswordResetTokenExpiredError("Password reset token has expired")

        # Marcar token como usado (uso único)
        await self.token_repository.mark_as_used(token_record)

        # Invalidar cualquier otro token activo del mismo usuario
        await self.token_repository.invalidate_all_for_user(token_record.user_id)

        # Revoke all active refresh tokens for this user immediately upon successful password reset
        if self.refresh_token_repository is not None:
            await self.refresh_token_repository.revoke_all_by_user_id(token_record.user_id)

        # Obtener usuario y actualizar contraseña
        user = await self.user_repository.get_by_id(token_record.user_id)
        if user is None:
            raise PasswordResetError("User associated with token not found")

        user.hashed_password = password_hasher.hash(new_password)
        await self.user_repository.update(user)

        return token_record.user_id

    async def _send_reset_email(self, to_email: str, token: str) -> None:
        """Envía el email de reset de contraseña al usuario."""
        reset_link = f"{settings.app_url}/auth/reset-password?token={token}"
        expire_hours = settings.password_reset_token_expire_hours
        body_html = (
            f"<h1>Reset your password</h1>"
            f"<p>Click the link below to reset your password:</p>"
            f"<p><a href='{reset_link}'>{reset_link}</a></p>"
            f"<p>This link expires in {expire_hours} hour(s).</p>"
            f"<p>If you did not request a password reset, please ignore this email.</p>"
        )
        body_text = (
            f"Reset your password\n\n"
            f"Click the link below to reset your password:\n\n"
            f"{reset_link}\n\n"
            f"This link expires in {expire_hours} hour(s).\n\n"
            f"If you did not request a password reset, please ignore this email."
        )

        await self.email_provider.send_email(
            to_email=to_email,
            subject="Reset your password",
            body_html=body_html,
            body_text=body_text,
        )