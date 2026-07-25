from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.exceptions import (
    PasswordResetError,
    PasswordResetTokenExpiredError,
    PasswordResetTokenNotFoundError,
)
from app.models.password_reset_token import PasswordResetToken
from app.models.role import Role
from app.models.user import User
from app.services.password_reset_service import PasswordResetService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fresh_user(*, email: str = "user@example.com") -> User:
    return User(
        email=email,
        hashed_password="hashed",
        role=Role.USER,
    )


def _make_repo_mocks() -> tuple[MagicMock, MagicMock]:
    user_repo = MagicMock()
    user_repo.get_by_email = AsyncMock()
    user_repo.get_by_id = AsyncMock()
    user_repo.update = AsyncMock()
    token_repo = MagicMock()
    token_repo.create = AsyncMock()
    token_repo.get_by_token = AsyncMock()
    token_repo.get_valid_by_user_id = AsyncMock()
    token_repo.mark_as_used = AsyncMock()
    token_repo.invalidate_all_for_user = AsyncMock()
    return user_repo, token_repo


# ---------------------------------------------------------------------------
# Tests – request_password_reset
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_request_password_reset_creates_token_for_existing_user():
    """Verifica que se crea un token para un usuario existente."""
    user_repo, token_repo = _make_repo_mocks()
    user = _make_fresh_user()
    user_repo.get_by_email.return_value = user
    token_repo.get_valid_by_user_id.return_value = None

    svc = PasswordResetService(
        user_repository=user_repo,
        token_repository=token_repo,
        email_provider=None,
    )

    await svc.request_password_reset("user@example.com")

    token_repo.create.assert_called_once()
    created_token = token_repo.create.call_args[0][0]
    assert created_token.user_id == str(user.id)
    assert created_token.token is not None
    assert created_token.expires_at > datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_request_password_reset_silently_ignores_missing_user():
    """Verifica que no se revela si el email no existe (seguridad)."""
    user_repo, token_repo = _make_repo_mocks()
    user_repo.get_by_email.return_value = None

    svc = PasswordResetService(
        user_repository=user_repo,
        token_repository=token_repo,
        email_provider=None,
    )

    # No debe lanzar excepción
    await svc.request_password_reset("nonexistent@example.com")

    token_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_request_password_reset_invalidates_previous_token():
    """Verifica que los tokens previos se invalidan al solicitar uno nuevo."""
    user_repo, token_repo = _make_repo_mocks()
    user = _make_fresh_user()
    user_repo.get_by_email.return_value = user

    previous_token = PasswordResetToken(
        user_id=str(user.id),
        token="old-token",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    token_repo.get_valid_by_user_id.return_value = previous_token

    svc = PasswordResetService(
        user_repository=user_repo,
        token_repository=token_repo,
        email_provider=None,
    )

    await svc.request_password_reset("user@example.com")

    # Verificar que se marcó como usado el token anterior
    token_repo.mark_as_used.assert_called_once_with(previous_token)


@pytest.mark.asyncio
async def test_request_password_reset_calls_email_provider():
    """Verifica que se llama al provider de email si está configurado."""
    user_repo, token_repo = _make_repo_mocks()
    user = _make_fresh_user(email="test@example.com")
    user_repo.get_by_email.return_value = user
    token_repo.get_valid_by_user_id.return_value = None

    email_provider = MagicMock()
    email_provider.send_email = AsyncMock()

    svc = PasswordResetService(
        user_repository=user_repo,
        token_repository=token_repo,
        email_provider=email_provider,
    )

    await svc.request_password_reset("test@example.com")

    email_provider.send_email.assert_called_once()
    call_kwargs = email_provider.send_email.call_args[1]
    assert call_kwargs["to_email"] == "test@example.com"
    assert "reset" in call_kwargs["subject"].lower()
    assert "reset" in call_kwargs["body_html"].lower()


# ---------------------------------------------------------------------------
# Tests – reset_password
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reset_password_updates_password():
    """Verifica que reset_password actualiza la contraseña del usuario."""
    user_repo, token_repo = _make_repo_mocks()
    user = _make_fresh_user()

    valid_token = PasswordResetToken(
        user_id=str(user.id),
        token="valid-token-123",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    token_repo.get_by_token.return_value = valid_token
    user_repo.get_by_id.return_value = user
    user_repo.update.return_value = user

    svc = PasswordResetService(
        user_repository=user_repo,
        token_repository=token_repo,
        email_provider=None,
    )

    new_password = "NewSecurePass123!"
    await svc.reset_password("valid-token-123", new_password)

    token_repo.mark_as_used.assert_called_once_with(valid_token)
    token_repo.invalidate_all_for_user.assert_called_once_with(str(user.id))
    user_repo.update.assert_called_once_with(user)
    # Verificar que la contraseña se ha actualizado (hasheada)
    assert user.hashed_password != "hashed"
    assert user.hashed_password.startswith("$")


@pytest.mark.asyncio
async def test_reset_password_raises_when_token_not_found():
    """Verifica que lanza error si el token no existe."""
    user_repo, token_repo = _make_repo_mocks()
    token_repo.get_by_token.return_value = None

    svc = PasswordResetService(
        user_repository=user_repo,
        token_repository=token_repo,
        email_provider=None,
    )

    with pytest.raises(PasswordResetTokenNotFoundError, match="not found"):
        await svc.reset_password("nonexistent-token", "NewPass123!")


@pytest.mark.asyncio
async def test_reset_password_raises_when_token_expired():
    """Verifica que lanza error si el token ha expirado."""
    user_repo, token_repo = _make_repo_mocks()

    expired_token = PasswordResetToken(
        user_id="some-user-id",
        token="expired-token",
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    token_repo.get_by_token.return_value = expired_token

    svc = PasswordResetService(
        user_repository=user_repo,
        token_repository=token_repo,
        email_provider=None,
    )

    with pytest.raises(PasswordResetTokenExpiredError, match="expired"):
        await svc.reset_password("expired-token", "NewPass123!")


@pytest.mark.asyncio
async def test_reset_password_raises_when_token_used():
    """Verifica que lanza error si el token ya fue usado."""
    user_repo, token_repo = _make_repo_mocks()

    used_token = PasswordResetToken(
        user_id="some-user-id",
        token="used-token",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        is_used=True,
    )
    token_repo.get_by_token.return_value = used_token

    svc = PasswordResetService(
        user_repository=user_repo,
        token_repository=token_repo,
        email_provider=None,
    )

    with pytest.raises(PasswordResetTokenExpiredError, match="used"):
        await svc.reset_password("used-token", "NewPass123!")


@pytest.mark.asyncio
async def test_reset_password_raises_when_user_not_found():
    """Verifica que lanza error si el usuario asociado al token no existe."""
    user_repo, token_repo = _make_repo_mocks()

    valid_token = PasswordResetToken(
        user_id="nonexistent-user-id",
        token="valid-token",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    token_repo.get_by_token.return_value = valid_token
    user_repo.get_by_id.return_value = None

    svc = PasswordResetService(
        user_repository=user_repo,
        token_repository=token_repo,
        email_provider=None,
    )

    with pytest.raises(PasswordResetError, match="not found"):
        await svc.reset_password("valid-token", "NewPass123!")


# ---------------------------------------------------------------------------
# Tests – token generation
# ---------------------------------------------------------------------------


def test_generate_token_returns_urlsafe_string():
    """Verifica que _generate_token retorna un string seguro."""
    token = PasswordResetService._generate_token()
    assert isinstance(token, str)
    assert len(token) > 20  # 48 bytes en base64url ~ 64 caracteres
    # No debe contener caracteres no seguros para URL
    assert "+" not in token
    assert "/" not in token
    assert "=" not in token