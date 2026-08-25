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
        """Registra el token FCM del usuario.

        El ``token`` identifica al dispositivo (único en BD): si ya existe se
        actualiza su dueño/plataforma (p.ej. tras logout/login). Si no existe
        pero el usuario ya tiene un token para esa plataforma, se sustituye.
        TEST.API.DOMAIN fix: antes un re-registro del mismo token con otra
        plataforma violaba el UNIQUE(token) y devolvía 500.
        """
        now = datetime.now(UTC)

        result = await self.session.execute(
            select(PushToken).where(PushToken.token == token)
        )
        push_token = result.scalar_one_or_none()
        if push_token is not None:
            push_token.user_id = str(user_id)
            push_token.platform = platform
            push_token.updated_at = now
            await self.session.commit()
            await self.session.refresh(push_token)
            return push_token

        result = await self.session.execute(
            select(PushToken).where(
                PushToken.user_id == str(user_id),
                PushToken.platform == platform,
            )
        )
        existing_for_platform = result.scalar_one_or_none()
        if existing_for_platform is not None:
            existing_for_platform.token = token
            existing_for_platform.updated_at = now
            await self.session.commit()
            await self.session.refresh(existing_for_platform)
            return existing_for_platform

        push_token = PushToken(user_id=str(user_id), token=token, platform=platform)
        self.session.add(push_token)
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

    async def delete_by_token(self, token: str) -> None:
        """Elimina el token FCM (p.ej. al hacer logout o cuando es inválido)."""
        result = await self.session.execute(select(PushToken).where(PushToken.token == token))
        push_token = result.scalar_one_or_none()
        if push_token is not None:
            await self.session.delete(push_token)
            await self.session.commit()
