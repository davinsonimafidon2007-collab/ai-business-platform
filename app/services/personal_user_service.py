"""Servicio de usuario personal/local cuando AUTH_DISABLED=true.

En lugar de devolver un SimpleNamespace quimérico, hace get-or-create de una
fila real en la tabla ``users``: las rutas (vehicles, deals, searches, api_keys,
dashboard, opportunities, inspection) usan ``current_user.id`` como FK, así que
sin fila real fallarían. La fila se crea una sola vez y se reutiliza.
"""

from __future__ import annotations

from app.core.local_user import (
    LOCAL_USER_EMAIL,
    LOCAL_USER_FULL_NAME,
    LOCAL_USER_ID_STR,
)
from app.models.role import Role
from app.models.user import User
from app.repositories.user_repository import UserRepository


class PersonalUserService:
    """Reutiliza (o crea) el usuario local ADMIN persistente."""

    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    async def ensure_local_user(self) -> User:
        user = await self.repository.get_by_email(LOCAL_USER_EMAIL)
        if user is not None:
            return user

        user = User(
            id=LOCAL_USER_ID_STR,
            email=LOCAL_USER_EMAIL,
            # El local user no hace login por contraseña; vacío a propósito.
            hashed_password="",
            full_name=LOCAL_USER_FULL_NAME,
            is_active=True,
            is_verified=True,
            role=Role.ADMIN,
        )
        await self.repository.create(user)
        return user
