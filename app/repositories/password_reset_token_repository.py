from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.password_reset_token import PasswordResetToken


class PasswordResetTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, token: PasswordResetToken) -> PasswordResetToken:
        self.session.add(token)
        await self.session.commit()
        await self.session.refresh(token)
        return token

    async def get_by_token(self, token: str) -> PasswordResetToken | None:
        result = await self.session.execute(
            select(PasswordResetToken).where(PasswordResetToken.token == token)
        )
        return result.scalar_one_or_none()

    async def get_valid_by_user_id(self, user_id: str) -> PasswordResetToken | None:
        """Retorna el último token no usado y no expirado para un usuario."""
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.is_used == False,
                PasswordResetToken.expires_at > now,
            )
            .order_by(PasswordResetToken.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def mark_as_used(self, token: PasswordResetToken) -> PasswordResetToken:
        token.is_used = True
        token.used_at = datetime.now(timezone.utc)
        self.session.add(token)
        await self.session.commit()
        await self.session.refresh(token)
        return token

    async def invalidate_all_for_user(self, user_id: str) -> None:
        """Invalida todos los tokens de reset no usados para un usuario."""
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.is_used == False,
                PasswordResetToken.expires_at > now,
            )
        )
        tokens = result.scalars().all()
        for token in tokens:
            token.is_used = True
            token.used_at = now
            self.session.add(token)
        await self.session.commit()