from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, refresh_token: RefreshToken) -> RefreshToken:
        self.session.add(refresh_token)
        await self.session.commit()
        await self.session.refresh(refresh_token)
        return refresh_token

    async def get_by_token(self, token: str) -> RefreshToken | None:
        result = await self.session.execute(select(RefreshToken).where(RefreshToken.token == token))
        return result.scalar_one_or_none()

    async def revoke_by_token(self, token: str) -> None:
        result = await self.session.execute(select(RefreshToken).where(RefreshToken.token == token))
        refresh_token = result.scalar_one_or_none()
        if refresh_token:
            refresh_token.is_revoked = True
            refresh_token.revoked_at = datetime.now(timezone.utc)
            await self.session.commit()

    async def revoke_all_by_user_id(self, user_id: UUID | str) -> None:
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.user_id == str(user_id), RefreshToken.is_revoked == False)
        )
        tokens = result.scalars().all()
        for token in tokens:
            token.is_revoked = True
            token.revoked_at = datetime.now(timezone.utc)
        if tokens:
            await self.session.commit()