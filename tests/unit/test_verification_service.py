from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.exceptions import AuthenticationError, VerificationTokenExpiredError, VerificationTokenNotFoundError
from app.models.role import Role
from app.models.user import User
from app.models.verification_token import VerificationToken
from app.services.verification_service import VERIFICATION_TOKEN_EXPIRE_HOURS, VerificationService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fresh_user(*, email: str = "user@example.com", is_verified: bool = False) -> User:
    return User(
        email=email,
        hashed_password="hashed",
        role=Role.USER,
        is_verified=is_verified,
    )


def _make_repo_mocks() -> tuple[MagicMock, MagicMock]:
    user_repo = MagicMock()
    user_repo.get_by_id = AsyncMock()
    user_repo.update = AsyncMock()
    token_repo = MagicMock()
    token_repo.create = AsyncMock()
    token_repo.get_by_token = AsyncMock()
    token_repo.get_valid_by_user_id = AsyncMock()
    token_repo.mark_as_used = AsyncMock()
    return user_repo, token_repo


# ---------------------------------------------------------------------------
# Tests – request_verification
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_request_verification_creates_token_for_unverified_user():
    """Verifica que se crea un token para usuario no verificado."""
    user_repo, token_repo = _make_repo_mocks()
    user = _make_fresh_user()
    token_repo.get_valid_by_user_id.return_value = None

    svc = VerificationService(
        user_repository=user_repo,
        token_repository=token_repo,
        email_provider=None,
    )

    result = await svc.request_verification(user)

    token_repo.create.assert_called_once()
    created_token = token_repo.create.call_args[0][0]
    assert created_token.user_id == str(user.id)
    assert created_token.token is not None
    assert created_token.expires_at > datetime.now(timezone.utc)
    assert result is not None


@pytest.mark.asyncio
async def test_request_verification_invalidates_previous_token():
    """Verifica que los tokens previos se invalidan al solicitar uno nuevo."""
    user_repo, token_repo = _make_repo_mocks()
    user = _make_fresh_user()

    previous_token = VerificationToken(
        user_id=str(user.id),
        token="old-token",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    token_repo.get_valid_by_user_id.return_value = previous_token

    svc = VerificationService(
        user_repository=user_repo,
        token_repository=token_repo,
        email_provider=None,
    )

    await svc.request_verification(user)

    # Verificar que se marcó como usado el token anterior
    token_repo.mark_as_used.assert_called_once_with(previous_token)


@pytest.mark.asyncio
async def test_request_verification_raises_when_already_verified():
    """Verifica que lanza error si el usuario ya está verificado."""
    user_repo, token_repo = _make_repo_mocks()
    user = _make_fresh_user(is_verified=True)

    svc = VerificationService(
        user_repository=user_repo,
        token_repository=token_repo,
        email_provider=None,
    )

    with pytest.raises(AuthenticationError, match="already verified"):
        await svc.request_verification(user)

    token_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_request_verification_calls_email_provider():
    """Verifica que se llama al provider de email si está configurado."""
    user_repo, token_repo = _make_repo_mocks()
    user = _make_fresh_user(email="test@example.com")
    token_repo.get_valid_by_user_id.return_value = None

    email_provider = MagicMock()
    email_provider.send_email = AsyncMock()

    svc = VerificationService(
        user_repository=user_repo,
        token_repository=token_repo,
        email_provider=email_provider,
    )

    await svc.request_verification(user)

    email_provider.send_email.assert_called_once()
    call_kwargs = email_provider.send_email.call_args[1]
    assert call_kwargs["to_email"] == "test@example.com"
    assert "verify" in call_kwargs["subject"].lower()
    assert "verify" in call_kwargs["body_html"].lower()


# ---------------------------------------------------------------------------
# Tests – confirm_verification
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confirm_verification_marks_user_as_verified():
    """Verifica que confirm_verification marca al usuario como verificado."""
    user_repo, token_repo = _make_repo_mocks()
    user = _make_fresh_user()

    valid_token = VerificationToken(
        user_id=str(user.id),
        token="valid-token-123",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    token_repo.get_by_token.return_value = valid_token
    user_repo.get_by_id.return_value = user
    user_repo.update.return_value = user

    svc = VerificationService(
        user_repository=user_repo,
        token_repository=token_repo,
        email_provider=None,
    )

    result = await svc.confirm_verification("valid-token-123")

    assert result.is_verified is True
    token_repo.mark_as_used.assert_called_once_with(valid_token)
    user_repo.update.assert_called_once_with(user)


@pytest.mark.asyncio
async def test_confirm_verification_raises_when_token_not_found():
    """Verifica que lanza error si el token no existe."""
    user_repo, token_repo = _make_repo_mocks()
    token_repo.get_by_token.return_value = None

    svc = VerificationService(
        user_repository=user_repo,
        token_repository=token_repo,
        email_provider=None,
    )

    with pytest.raises(VerificationTokenNotFoundError, match="not found"):
        await svc.confirm_verification("nonexistent-token")


@pytest.mark.asyncio
async def test_confirm_verification_raises_when_token_expired():
    """Verifica que lanza error si el token ha expirado."""
    user_repo, token_repo = _make_repo_mocks()

    expired_token = VerificationToken(
        user_id="some-user-id",
        token="expired-token",
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    token_repo.get_by_token.return_value = expired_token

    svc = VerificationService(
        user_repository=user_repo,
        token_repository=token_repo,
        email_provider=None,
    )

    with pytest.raises(VerificationTokenExpiredError, match="expired"):
        await svc.confirm_verification("expired-token")


@pytest.mark.asyncio
async def test_confirm_verification_raises_when_token_used():
    """Verifica que lanza error si el token ya fue usado."""
    user_repo, token_repo = _make_repo_mocks()

    used_token = VerificationToken(
        user_id="some-user-id",
        token="used-token",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        is_used=True,
    )
    token_repo.get_by_token.return_value = used_token

    svc = VerificationService(
        user_repository=user_repo,
        token_repository=token_repo,
        email_provider=None,
    )

    with pytest.raises(VerificationTokenExpiredError, match="used"):
        await svc.confirm_verification("used-token")


# ---------------------------------------------------------------------------
# Tests – token generation
# ---------------------------------------------------------------------------


def test_generate_token_returns_urlsafe_string():
    """Verifica que _generate_token retorna un string seguro."""
    token = VerificationService._generate_token()
    assert isinstance(token, str)
    assert len(token) > 20  # 48 bytes en base64url ~ 64 caracteres
    # No debe contener caracteres no seguros para URL
    assert "+" not in token
    assert "/" not in token
    assert "=" not in token