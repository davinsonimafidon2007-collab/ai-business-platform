from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.verification_token import VerificationToken


class VerificationTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, token: VerificationToken) -> VerificationToken:
        self.session.add(token)
        await self.session.commit()
        await self.session.refresh(token)
        return token

    async def get_by_token(self, token: str) -> VerificationToken | None:
        result = await self.session.execute(
            select(VerificationToken).where(VerificationToken.token == token)
        )
        return result.scalar_one_or_none()

    async def get_valid_by_user_id(self, user_id: str) -> VerificationToken | None:
        """Retorna el último token no usado y no expirado para un usuario."""
        now = datetime.now(UTC)
        result = await self.session.execute(
            select(VerificationToken)
            .where(
                VerificationToken.user_id == user_id,
                VerificationToken.is_used == False,
                VerificationToken.expires_at > now,
            )
            .order_by(VerificationToken.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def mark_as_used(self, token: VerificationToken) -> VerificationToken:
        token.is_used = True
        token.used_at = datetime.now(UTC)
        self.session.add(token)
        await self.session.commit()
        await self.session.refresh(token)
        return token