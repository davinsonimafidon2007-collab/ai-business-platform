from __future__ import annotations

import time
from collections import defaultdict
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.config import settings
from app.models.role import Role

# ── Rate limit configuration per role ──────────────────────────────────────
ROLE_RATE_LIMITS: dict[Role, int] = {
    Role.ADMIN: settings.rate_limit_premium,
    Role.USER: settings.rate_limit_user,
}

# Default limit for unauthenticated requests
DEFAULT_RATE_LIMIT: int = settings.rate_limit_global


class RateLimitEntry:
    """Tracks request count and window start for rate limiting."""

    def __init__(self) -> None:
        self.count: int = 0
        self.window_start: float = time.time()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Configurable rate limiting middleware.

    Supports rate limiting by:
    - IP address (for unauthenticated requests)
    - User ID (for JWT-authenticated requests)
    - API Key prefix (for API key-authenticated requests)
    - Endpoint path

    Uses a sliding window approach with configurable limits per role.
    """

    def __init__(
        self,
        app: Any,
        *,
        window_seconds: int = 60,
    ) -> None:
        super().__init__(app)
        self.window_seconds = window_seconds
        # Stores: {key_type: {identifier: RateLimitEntry}}
        self._ip_limits: dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)
        self._user_limits: dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)
        self._api_key_limits: dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)
        self._endpoint_limits: dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        # Skip rate limiting for health endpoint
        if request.url.path == "/health":
            return await call_next(request)

        # Determine the rate limit key and limit based on auth method
        client_ip = request.client.host if request.client else "unknown"
        user = getattr(request.state, "user", None)
        auth_method = getattr(request.state, "auth_method", None)

        # Check endpoint-level rate limit
        endpoint_key = f"{request.method}:{request.url.path}"
        if not self._check_limit(self._endpoint_limits, endpoint_key, DEFAULT_RATE_LIMIT):
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
                headers={"Retry-After": str(self.window_seconds)},
            )

        if auth_method == "jwt" and user:
            # Rate limit by user ID with role-based limits
            role = user.role if hasattr(user, "role") else Role.USER
            limit = ROLE_RATE_LIMITS.get(role, DEFAULT_RATE_LIMIT)
            if not self._check_limit(self._user_limits, user.id, limit):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please try again later."},
                    headers={"Retry-After": str(self.window_seconds)},
                )
        elif auth_method == "api_key" and user:
            # Rate limit by user ID with role-based limits
            role = user.role if hasattr(user, "role") else Role.USER
            limit = ROLE_RATE_LIMITS.get(role, DEFAULT_RATE_LIMIT)
            if not self._check_limit(self._api_key_limits, user.id, limit):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please try again later."},
                    headers={"Retry-After": str(self.window_seconds)},
                )
        else:
            # Rate limit by IP for unauthenticated requests
            if not self._check_limit(self._ip_limits, client_ip, DEFAULT_RATE_LIMIT):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please try again later."},
                    headers={"Retry-After": str(self.window_seconds)},
                )

        return await call_next(request)

    def _check_limit(
        self,
        limits: dict[str, RateLimitEntry],
        key: str,
        max_requests: int,
    ) -> bool:
        """Check if the request is within the rate limit.

        Uses a sliding window approach. Resets the window if the
        current time window has expired.
        """
        now = time.time()
        entry = limits.setdefault(key, RateLimitEntry())

        # Reset window if expired
        if now - entry.window_start > self.window_seconds:
            entry.count = 0
            entry.window_start = now

        # Check limit
        if entry.count >= max_requests:
            return False

        entry.count += 1
        return True
