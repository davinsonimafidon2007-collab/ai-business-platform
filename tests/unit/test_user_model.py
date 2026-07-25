from app.models.user import User


def test_user_model_has_expected_columns() -> None:
    columns = {column.name for column in User.__table__.columns}

    assert {"id", "email", "hashed_password", "full_name", "is_active", "created_at", "updated_at"}.issubset(columns)
