"""Firebase Admin SDK initialization for Google ID token verification.

Uses the FIREBASE_CREDENTIALS_JSON environment variable to load
service account credentials. If not set, falls back to
FIREBASE_PROJECT_ID for metadata server-based discovery.
"""

from __future__ import annotations

import json
import logging
import os

from app.core.config import settings

logger = logging.getLogger(__name__)

_firebase_app = None


def _handle_firebase_unavailable(reason: str) -> None:
    """Handle a Firebase-not-available situation.

    In production with ``firebase_required=True`` this fails fast by raising a
    RuntimeError so the app refuses to boot (SEC-001). Otherwise it logs an
    ERROR in production (Google Login disabled) or a WARNING in dev/test and
    returns control to the caller, which returns None.
    """
    if settings.environment == "production" and settings.firebase_required:
        raise RuntimeError(
            "Firebase is required (FIREBASE_REQUIRED=true) in production but "
            f"cannot be configured: {reason}"
        )
    if settings.environment == "production":
        logger.error(
            "Firebase is not configured (%s). Google Login is DISABLED.", reason
        )
    else:
        logger.warning(
            "Firebase is not configured (%s). Google Login will not work until "
            "it is configured.",
            reason,
        )


def get_firebase_app():
    """Initialize and return the Firebase Admin SDK app singleton.

    Credentials priority:
    1. FIREBASE_CREDENTIALS_JSON env var (JSON string)
    2. FIREBASE_CREDENTIALS_PATH env var (path to JSON file)
    3. GOOGLE_APPLICATION_CREDENTIALS (ADC)

    Production fail-fast (SEC-001): if ``FIREBASE_REQUIRED=true`` and no
    credentials are available, a RuntimeError is raised so the app refuses to
    boot rather than silently disabling Google Login.
    """
    global _firebase_app

    if _firebase_app is not None:
        return _firebase_app

    try:
        import firebase_admin
        from firebase_admin import credentials
    except ImportError:
        _handle_firebase_unavailable("firebase_admin package is not installed")
        return None

    creds_json = os.environ.get("FIREBASE_CREDENTIALS_JSON") or (
        getattr(settings, "firebase_credentials_json", None) or None
    )
    creds_path = os.environ.get("FIREBASE_CREDENTIALS_PATH") or (
        getattr(settings, "firebase_credentials_path", None) or None
    )
    if creds_json == "":
        creds_json = None
    if creds_path == "":
        creds_path = None

    # Nothing configured anywhere -> treat as missing credentials (fail-fast
    # in production when required). Never log credential contents.
    if not creds_json and not creds_path and not os.environ.get(
        "GOOGLE_APPLICATION_CREDENTIALS"
    ):
        _handle_firebase_unavailable(
            "no credentials (set FIREBASE_CREDENTIALS_JSON or "
            "FIREBASE_CREDENTIALS_PATH, or GOOGLE_APPLICATION_CREDENTIALS)"
        )
        return None

    try:
        if creds_json:
            cred = credentials.Certificate(json.loads(creds_json))
            _firebase_app = firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized from JSON env var")
        elif creds_path:
            cred = credentials.Certificate(creds_path)
            _firebase_app = firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized from file: %s", creds_path)
        else:
            # Try Application Default Credentials
            _firebase_app = firebase_admin.initialize_app()
            logger.info("Firebase Admin SDK initialized with ADC")
    except Exception as exc:
        _handle_firebase_unavailable(f"initialization failed: {exc}")
        _firebase_app = None

    return _firebase_app


async def verify_google_id_token(id_token: str) -> dict:
    """Verify a Firebase ID token and return the decoded claims.

    Args:
        id_token: Firebase ID token from the frontend.

    Returns:
        Decoded token dict with keys: uid, email, email_verified, name, picture, etc.

    Raises:
        ValueError: If the token is invalid or Firebase is not configured.
    """
    app = get_firebase_app()
    if app is None:
        raise ValueError(
            "Firebase is not configured. Set FIREBASE_CREDENTIALS_JSON "
            "or FIREBASE_CREDENTIALS_PATH environment variable."
        )

    from firebase_admin import auth as firebase_auth

    try:
        decoded = firebase_auth.verify_id_token(id_token, app=app, clock_skew_seconds=10)
        return {
            "uid": decoded.get("uid", ""),
            "email": decoded.get("email", ""),
            "email_verified": decoded.get("email_verified", False),
            "name": decoded.get("name", ""),
            "picture": decoded.get("picture", ""),
        }
    except firebase_auth.ExpiredIdTokenError as exc:
        raise ValueError("Firebase ID token has expired") from exc
    except firebase_auth.RevokedIdTokenError as exc:
        raise ValueError("Firebase ID token has been revoked") from exc
    except firebase_auth.InvalidIdTokenError as exc:
        raise ValueError(f"Invalid Firebase ID token: {exc}") from exc