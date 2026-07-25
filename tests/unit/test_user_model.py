from app.models.role import Role
from app.models.user import User


def test_user_model_has_expected_columns() -> None:
    columns = {column.name for column in User.__table__.columns}

    assert {"id", "email", "hashed_password", "full_name", "is_active", "role", "created_at", "updated_at"}.issubset(columns)


def test_user_model_defaults_to_user_role() -> None:
    user = User(email="user@example.com", hashed_password="secret")

    assert user.role is Role.USER
