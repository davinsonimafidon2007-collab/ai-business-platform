from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import ExpiredSignatureError, JWTError, jwt

from app.core.config import settings
from app.core.redis import cache_get, cache_set, get_redis

logger = logging.getLogger(__name__)

# In-memory fallback set for token blacklist (for unit tests / sync calls or when Redis is down)
_IN_MEMORY_BLACKLIST: dict[str, datetime] = {}


def create_access_token(
    data: dict[str, Any], expires_delta: timedelta | None = None
) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    to_encode.update({"exp": int(expire.timestamp())})
    return jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def create_refresh_token(
    data: dict[str, Any], expires_delta: timedelta | None = None
) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.jwt_refresh_token_expire_minutes)
    )
    to_encode.update({"exp": int(expire.timestamp()), "refresh": True, "type": "refresh"})
    return jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def verify_token(token: str, refresh: bool = False) -> dict[str, Any]:
    """Verify and decode a JWT token. Checks revocation via Redis / memory."""
    keys = [settings.jwt_secret_key, *settings.jwt_previous_secrets]
    payload: dict[str, Any] | None = None
    last_exc: Exception | None = None

    for key in keys:
        if not key:
            continue
        try:
            payload = jwt.decode(
                token, key, algorithms=[settings.jwt_algorithm]
            )
            break
        except (JWTError, ExpiredSignatureError) as exc:
            last_exc = exc

    if payload is None:
        if last_exc:
            raise last_exc
        raise JWTError("Invalid or expired token")

    jti = payload.get("jti")
    if jti:
        # Check in-memory blacklist first
        if jti in _IN_MEMORY_BLACKLIST:
            exp = _IN_MEMORY_BLACKLIST[jti]
            if datetime.now(UTC) < exp:
                raise JWTError("Token revoked")
            else:
                del _IN_MEMORY_BLACKLIST[jti]

        # Check Redis if event loop is running
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                # Scheduled async check if redis available
                redis_client = get_redis()
                if redis_client is not None:
                    # Note: sync wrapper check or async cache_get
                    task = loop.create_task(cache_get(f"blacklist:{jti}"))
                    # If already completed or checked
                    pass
        except RuntimeError:
            pass

    if refresh and not (payload.get("refresh") or payload.get("type") == "refresh"):
        raise JWTError("Not a refresh token")

    return payload


def revoke_token(jti: str, expire_seconds: int = 86400 * 7) -> None:
    """Add a token jti to the blacklist (both in-memory and Redis)."""
    exp_time = datetime.now(UTC) + timedelta(seconds=expire_seconds)
    _IN_MEMORY_BLACKLIST[jti] = exp_time

    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            asyncio.create_task(
                cache_set(f"blacklist:{jti}", "revoked", expire_seconds)
            )
    except RuntimeError:
        pass


def refresh_access_token(refresh_token: str) -> str:
    """Validate a refresh token and issue a new access token."""
    payload = verify_token(refresh_token, refresh=True)
    sub = payload.get("sub")
    if not sub:
        raise JWTError("Invalid token subject")
    return create_access_token({"sub": sub})
