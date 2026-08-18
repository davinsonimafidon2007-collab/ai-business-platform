from datetime import timedelta

import pytest
from jose import ExpiredSignatureError, JWTError

from app.core.auth import (
    create_access_token,
    create_refresh_token,
    refresh_access_token,
    revoke_token,
    verify_token,
)


def test_jwt_creation_and_verification():
    token = create_access_token({"sub": "test_user_id"})
    payload = verify_token(token)
    assert payload["sub"] == "test_user_id"


def test_jwt_expired():
    token = create_access_token({"sub": "test_user_id"}, expires_delta=timedelta(seconds=-1))
    with pytest.raises((ExpiredSignatureError, JWTError)):
        verify_token(token)


def test_jwt_revocation():
    token = create_access_token({"sub": "test_user_id", "jti": "revoked_jti_123"})
    revoke_token("revoked_jti_123")
    with pytest.raises(JWTError):
        verify_token(token)


def test_jwt_refresh_token():
    refresh_tok = create_refresh_token({"sub": "user_456"})
    new_access_tok = refresh_access_token(refresh_tok)
    payload = verify_token(new_access_tok)
    assert payload["sub"] == "user_456"
