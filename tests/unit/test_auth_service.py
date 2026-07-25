from unittest.mock import AsyncMock

import pytest

from app.exceptions import InvalidCredentialsError, UserAlreadyExistsError
from app.models.user import User
from app.services.auth_service import AuthService, password_hasher


@pytest.mark.asyncio
async def test_register_user_successfully() -> None:
    repository = AsyncMock()
    repository.get_by_email.return_value = None
    repository.create.return_value = User(email="new@example.com", hashed_password="hashed")

    service = AuthService(repository)
    user = await service.register_user(email="new@example.com", password="secret")

    assert user.email == "new@example.com"
    assert user.hashed_password != "secret"
    repository.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_register_user_raises_when_email_exists() -> None:
    repository = AsyncMock()
    repository.get_by_email.return_value = User(email="existing@example.com", hashed_password="hashed")

    service = AuthService(repository)

    with pytest.raises(UserAlreadyExistsError):
        await service.register_user(email="existing@example.com", password="secret")


@pytest.mark.asyncio
async def test_authenticate_user_successfully() -> None:
    repository = AsyncMock()
    repository.get_by_email.return_value = User(
        email="user@example.com",
        hashed_password=password_hasher.hash("secret"),
    )

    service = AuthService(repository)
    user = await service.authenticate_user(email="user@example.com", password="secret")

    assert user.email == "user@example.com"


@pytest.mark.asyncio
async def test_authenticate_user_raises_for_invalid_password() -> None:
    repository = AsyncMock()
    repository.get_by_email.return_value = User(
        email="user@example.com",
        hashed_password=password_hasher.hash("secret"),
    )

    service = AuthService(repository)

    with pytest.raises(InvalidCredentialsError):
        await service.authenticate_user(email="user@example.com", password="wrong-password")
