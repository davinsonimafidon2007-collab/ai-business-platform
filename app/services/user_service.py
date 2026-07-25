from __future__ import annotations

from typing import Any
from uuid import UUID

from app.exceptions import UserAlreadyExistsError, UserNotFoundError
from app.models.user import User
from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    async def create_user(self, *, email: str, hashed_password: str, full_name: str | None = None) -> User:
        existing_user = await self.repository.get_by_email(email)
        if existing_user is not None:
            raise UserAlreadyExistsError(f"User with email '{email}' already exists")

        user = User(email=email, hashed_password=hashed_password, full_name=full_name)
        return await self.repository.create(user)

    async def get_user(self, user_id: UUID | str) -> User:
        user = await self.repository.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(f"User with id '{user_id}' was not found")
        return user

    async def list_users(self) -> list[User]:
        return await self.repository.list()

    async def update_user(self, user_id: UUID | str, **updates: Any) -> User:
        user = await self.get_user(user_id)

        if "email" in updates and updates["email"] is not None:
            existing_user = await self.repository.get_by_email(updates["email"])
            if existing_user is not None and existing_user.id != str(user.id):
                raise UserAlreadyExistsError(f"User with email '{updates['email']}' already exists")
            user.email = updates["email"]

        if "full_name" in updates:
            user.full_name = updates["full_name"]

        if "hashed_password" in updates and updates["hashed_password"] is not None:
            user.hashed_password = updates["hashed_password"]

        if "is_active" in updates:
            user.is_active = updates["is_active"]

        return await self.repository.update(user)

    async def delete_user(self, user_id: UUID | str) -> None:
        user = await self.get_user(user_id)
        await self.repository.delete(user)
