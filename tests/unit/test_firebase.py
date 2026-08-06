"""Unit tests for app.core.firebase (Task FIRE.1).

No real Firebase credentials required: all paths are mocked.
"""

from __future__ import annotations

import pytest

from app.core import firebase as firebase_mod


@pytest.fixture(autouse=True)
def reset_firebase_singleton():
    """Ensure singleton does not leak between tests."""
    firebase_mod._firebase_app = None
    yield
    firebase_mod._firebase_app = None


def test_get_firebase_app_returns_none_when_package_missing(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "firebase_admin" or name.startswith("firebase_admin."):
            raise ImportError("no firebase_admin")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert firebase_mod.get_firebase_app() is None


def test_get_firebase_app_uses_json_env(monkeypatch):
    fake_app = object()

    class FakeCreds:
        @staticmethod
        def Certificate(data):
            assert isinstance(data, dict)
            assert data.get("type") == "service_account"
            return "cred"

    class FakeAdmin:
        @staticmethod
        def initialize_app(cred):
            assert cred == "cred"
            return fake_app

    monkeypatch.setenv(
        "FIREBASE_CREDENTIALS_JSON",
        '{"type":"service_account","project_id":"demo"}',
    )
    monkeypatch.delenv("FIREBASE_CREDENTIALS_PATH", raising=False)

    import sys
    from types import ModuleType

    fa = ModuleType("firebase_admin")
    fa.initialize_app = FakeAdmin.initialize_app
    creds = ModuleType("firebase_admin.credentials")
    creds.Certificate = FakeCreds.Certificate
    monkeypatch.setitem(sys.modules, "firebase_admin", fa)
    monkeypatch.setitem(sys.modules, "firebase_admin.credentials", creds)

    app = firebase_mod.get_firebase_app()
    assert app is fake_app
    # singleton
    assert firebase_mod.get_firebase_app() is fake_app


@pytest.mark.asyncio
async def test_verify_google_id_token_raises_when_not_configured(monkeypatch):
    monkeypatch.setattr(firebase_mod, "get_firebase_app", lambda: None)
    with pytest.raises(ValueError, match="Firebase is not configured"):
        await firebase_mod.verify_google_id_token("any-token")


@pytest.mark.asyncio
async def test_verify_google_id_token_returns_claims(monkeypatch):
    fake_app = object()
    monkeypatch.setattr(firebase_mod, "get_firebase_app", lambda: fake_app)

    class FakeAuth:
        @staticmethod
        def verify_id_token(token, app=None, clock_skew_seconds=0):
            assert token == "good-token"
            assert app is fake_app
            return {
                "uid": "uid-99",
                "email": "u@example.com",
                "email_verified": True,
                "name": "U",
                "picture": "http://x",
            }

        class ExpiredIdTokenError(Exception):
            pass

        class RevokedIdTokenError(Exception):
            pass

        class InvalidIdTokenError(Exception):
            pass

    import sys
    from types import ModuleType

    fa = ModuleType("firebase_admin")
    fa_auth = ModuleType("firebase_admin.auth")
    for name in (
        "verify_id_token",
        "ExpiredIdTokenError",
        "RevokedIdTokenError",
        "InvalidIdTokenError",
    ):
        setattr(fa_auth, name, getattr(FakeAuth, name))
    monkeypatch.setitem(sys.modules, "firebase_admin", fa)
    monkeypatch.setitem(sys.modules, "firebase_admin.auth", fa_auth)

    claims = await firebase_mod.verify_google_id_token("good-token")
    assert claims["uid"] == "uid-99"
    assert claims["email"] == "u@example.com"
    assert claims["email_verified"] is True


@pytest.mark.asyncio
async def test_verify_google_id_token_maps_expired(monkeypatch):
    fake_app = object()
    monkeypatch.setattr(firebase_mod, "get_firebase_app", lambda: fake_app)

    class Expired(Exception):
        pass

    class FakeAuth:
        ExpiredIdTokenError = Expired
        RevokedIdTokenError = type("Revoked", (Exception,), {})
        InvalidIdTokenError = type("Invalid", (Exception,), {})

        @staticmethod
        def verify_id_token(*args, **kwargs):
            raise Expired()

    import sys
    from types import ModuleType

    fa = ModuleType("firebase_admin")
    fa_auth = ModuleType("firebase_admin.auth")
    for name in (
        "verify_id_token",
        "ExpiredIdTokenError",
        "RevokedIdTokenError",
        "InvalidIdTokenError",
    ):
        setattr(fa_auth, name, getattr(FakeAuth, name))
    monkeypatch.setitem(sys.modules, "firebase_admin", fa)
    monkeypatch.setitem(sys.modules, "firebase_admin.auth", fa_auth)

    with pytest.raises(ValueError, match="expired"):
        await firebase_mod.verify_google_id_token("old")
