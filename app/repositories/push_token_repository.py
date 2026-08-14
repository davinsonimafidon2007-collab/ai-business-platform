from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.push_token import PushToken


class PushTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(
        self,
        *,
        user_id: UUID | str,
        token: str,
        platform: str = "android",
    ) -> PushToken:
        """Registra el token FCM del usuario (un token por usuario+plataforma)."""
        result = await self.session.execute(
            select(PushToken).where(
                PushToken.user_id == str(user_id),
                PushToken.platform == platform,
            )
        )
        push_token = result.scalar_one_or_none()
        if push_token is None:
            push_token = PushToken(user_id=str(user_id), token=token, platform=platform)
            self.session.add(push_token)
        else:
            push_token.token = token
            push_token.updated_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(push_token)
        return push_token

    async def get_by_user_id(self, user_id: UUID | str) -> list[PushToken]:
        result = await self.session.execute(
            select(PushToken).where(PushToken.user_id == str(user_id))
        )
        return list(result.scalars().all())

    async def delete(self, push_token: PushToken) -> None:
        await self.session.delete(push_token)
        await self.session.commit()
