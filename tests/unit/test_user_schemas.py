import pytest
from pydantic import ValidationError

from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.models.role import Role


def test_user_create_accepts_valid_email() -> None:
    user = UserCreate(email="user@example.com", hashed_password="secret")

    assert user.email == "user@example.com"
    assert user.is_active is True


def test_user_create_rejects_invalid_email() -> None:
    with pytest.raises(ValidationError):
        UserCreate(email="not-an-email", hashed_password="secret")


def test_user_read_allows_model_attributes() -> None:
    user = UserRead(
        id="123e4567-e89b-12d3-a456-426614174000",
        email="user@example.com",
        full_name="Jane Doe",
        is_active=True,
        is_verified=False,
        role=Role.USER,
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00",
    )

    assert user.email == "user@example.com"
    assert user.full_name == "Jane Doe"
    assert user.role is Role.USER
    assert user.is_verified is False


def test_user_update_allows_partial_updates() -> None:
    user = UserUpdate(email="new@example.com")

    assert user.email == "new@example.com"
    assert user.is_active is None
