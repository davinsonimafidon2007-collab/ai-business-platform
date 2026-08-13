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


# --- Google / Firebase (Task FIRE.1) ---

@pytest.mark.asyncio
async def test_authenticate_with_google_creates_user_when_missing(monkeypatch) -> None:
    repository = AsyncMock()
    repository.get_by_email.return_value = None
    created = User(
        email="google@example.com",
        hashed_password="hashed",
        full_name="Google User",
        is_verified=True,
        is_active=True,
    )
    repository.create.return_value = created

    async def fake_verify(id_token: str) -> dict:
        assert id_token == "fake-firebase-id-token"
        return {
            "uid": "firebase-uid-1",
            "email": "google@example.com",
            "email_verified": True,
            "name": "Google User",
            "picture": "",
        }

    monkeypatch.setattr(
        "app.services.auth_service.verify_google_id_token",
        fake_verify,
    )

    service = AuthService(repository)
    user = await service.authenticate_with_google(id_token="fake-firebase-id-token")

    assert user.email == "google@example.com"
    repository.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_authenticate_with_google_returns_existing_user(monkeypatch) -> None:
    existing = User(
        email="google@example.com",
        hashed_password="hashed",
        is_active=True,
    )
    repository = AsyncMock()
    repository.get_by_email.return_value = existing

    async def fake_verify(id_token: str) -> dict:
        return {
            "uid": "firebase-uid-1",
            "email": "google@example.com",
            "email_verified": True,
            "name": "Google User",
        }

    monkeypatch.setattr(
        "app.services.auth_service.verify_google_id_token",
        fake_verify,
    )

    service = AuthService(repository)
    user = await service.authenticate_with_google(id_token="tok")

    assert user is existing
    repository.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_authenticate_with_google_rejects_inactive(monkeypatch) -> None:
    from app.exceptions import AuthenticationError

    inactive = User(
        email="google@example.com",
        hashed_password="hashed",
        is_active=False,
    )
    repository = AsyncMock()
    repository.get_by_email.return_value = inactive

    async def fake_verify(id_token: str) -> dict:
        return {"uid": "u", "email": "google@example.com", "email_verified": True}

    monkeypatch.setattr(
        "app.services.auth_service.verify_google_id_token",
        fake_verify,
    )

    service = AuthService(repository)
    with pytest.raises(AuthenticationError, match="inactive"):
        await service.authenticate_with_google(id_token="tok")


@pytest.mark.asyncio
async def test_authenticate_with_google_rejects_token_without_email(monkeypatch) -> None:
    from app.exceptions import AuthenticationError

    repository = AsyncMock()

    async def fake_verify(id_token: str) -> dict:
        return {"uid": "u", "email": "", "email_verified": False}

    monkeypatch.setattr(
        "app.services.auth_service.verify_google_id_token",
        fake_verify,
    )

    service = AuthService(repository)
    with pytest.raises(AuthenticationError, match="no email"):
        await service.authenticate_with_google(id_token="tok")


@pytest.mark.asyncio
async def test_authenticate_with_google_propagates_verify_error(monkeypatch) -> None:
    from app.exceptions import AuthenticationError

    repository = AsyncMock()

    async def fake_verify(id_token: str) -> dict:
        raise ValueError("Firebase is not configured")

    monkeypatch.setattr(
        "app.services.auth_service.verify_google_id_token",
        fake_verify,
    )

    service = AuthService(repository)
    with pytest.raises(AuthenticationError, match="Firebase is not configured"):
        await service.authenticate_with_google(id_token="tok")


def test_auth_service_jwt_secret_key_rotation(monkeypatch) -> None:
    """Verifica que se pueden decodificar tokens firmados con la clave secreta anterior (TASK-015)."""
    from jose import jwt

    from app.core.config import settings

    repository = AsyncMock()
    service = AuthService(repository)

    # 1) Configurar secreto anterior en settings
    monkeypatch.setattr(settings, "jwt_secret_key", "current_jwt_secret_key_that_is_at_least_32_chars")
    monkeypatch.setattr(settings, "jwt_previous_secret_key", "previous_jwt_secret_key_that_is_at_least_32_chars")

    # 2) Generar un token con la clave anterior (simulando que el usuario tenía una sesión antes de rotar la clave)
    payload = {"sub": "user-123", "exp": 9999999999}
    token_old = jwt.encode(payload, "previous_jwt_secret_key_that_is_at_least_32_chars", algorithm="HS256")

    # 3) Debe decodificar de forma exitosa usando la clave de rotación de respaldo
    decoded = service.decode_access_token(token_old)
    assert decoded["sub"] == "user-123"
