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


def get_firebase_app():
    """Initialize and return the Firebase Admin SDK app singleton.

    Credentials priority:
    1. FIREBASE_CREDENTIALS_JSON env var (JSON string)
    2. FIREBASE_CREDENTIALS_PATH env var (path to JSON file)
    3. GOOGLE_APPLICATION_CREDENTIALS (ADC)
    """
    global _firebase_app

    if _firebase_app is not None:
        return _firebase_app

    try:
        import firebase_admin
        from firebase_admin import credentials
    except ImportError:
        logger.warning(
            "firebase_admin package is not installed. "
            "Google Login will not work until it is installed."
        )
        return None

    creds_json = os.environ.get("FIREBASE_CREDENTIALS_JSON")
    creds_path = os.environ.get("FIREBASE_CREDENTIALS_PATH")

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
        logger.warning(
            "Firebase Admin SDK initialization failed: %s. "
            "Google Login will not work until Firebase is configured.",
            exc,
        )
        # Don't raise — the app should still work without Firebase for local dev
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
    except firebase_auth.ExpiredIdTokenError:
        raise ValueError("Firebase ID token has expired")
    except firebase_auth.RevokedIdTokenError:
        raise ValueError("Firebase ID token has been revoked")
    except firebase_auth.InvalidIdTokenError as exc:
        raise ValueError(f"Invalid Firebase ID token: {exc}")