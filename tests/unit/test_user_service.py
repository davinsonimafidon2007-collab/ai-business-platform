from unittest.mock import AsyncMock

import pytest

from app.exceptions import UserAlreadyExistsError, UserNotFoundError
from app.models.user import User
from app.services.user_service import UserService


@pytest.mark.asyncio
async def test_create_user_raises_when_email_exists() -> None:
    repository = AsyncMock()
    repository.get_by_email.return_value = User(email="existing@example.com", hashed_password="secret")

    service = UserService(repository)

    with pytest.raises(UserAlreadyExistsError):
        await service.create_user(email="existing@example.com", hashed_password="secret")


@pytest.mark.asyncio
async def test_create_user_successfully() -> None:
    repository = AsyncMock()
    repository.get_by_email.return_value = None
    repository.create.return_value = User(email="new@example.com", hashed_password="secret")

    service = UserService(repository)
    user = await service.create_user(email="new@example.com", hashed_password="secret")

    assert user.email == "new@example.com"
    repository.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_user_raises_when_missing() -> None:
    repository = AsyncMock()
    repository.get_by_id.return_value = None

    service = UserService(repository)

    with pytest.raises(UserNotFoundError):
        await service.get_user("missing-id")


@pytest.mark.asyncio
async def test_update_user_raises_when_email_taken_by_another_user() -> None:
    repository = AsyncMock()
    existing = User(id="1", email="owner@example.com", hashed_password="old")
    repository.get_by_id.return_value = existing
    repository.get_by_email.return_value = User(id="2", email="taken@example.com", hashed_password="secret")

    service = UserService(repository)

    with pytest.raises(UserAlreadyExistsError):
        await service.update_user("1", email="taken@example.com")
