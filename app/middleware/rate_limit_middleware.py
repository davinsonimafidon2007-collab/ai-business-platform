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
        path = request.url.path

        # Health (montado bajo /api/v1 y posible alias raíz)
        if path in ("/health", "/api/v1/health"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        user = getattr(request.state, "user", None)
        auth_method = getattr(request.state, "auth_method", None)

        # Límites específicos por endpoint sensible (antes del genérico)
        endpoint_key = f"{request.method}:{path}"
        if path in ("/api/v1/auth/login", "/api/v1/auth/google") and request.method == "POST":
            endpoint_limit = settings.rate_limit_login
        elif path == "/api/v1/auth/register" and request.method == "POST":
            endpoint_limit = settings.rate_limit_register
        else:
            endpoint_limit = DEFAULT_RATE_LIMIT

        if not self._check_limit(self._endpoint_limits, endpoint_key, endpoint_limit):
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
                headers={"Retry-After": str(self.window_seconds)},
            )

        # Límites por identidad
        if user is not None and auth_method == "jwt":
            role = getattr(user, "role", None)
            limit = ROLE_RATE_LIMITS.get(role, DEFAULT_RATE_LIMIT) if role else DEFAULT_RATE_LIMIT
            if not self._check_limit(self._user_limits, str(user.id), limit):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please try again later."},
                    headers={"Retry-After": str(self.window_seconds)},
                )
        elif auth_method == "api_key":
            # Usar el mismo techo de usuario autenticado (premium si role disponible)
            role = getattr(user, "role", None) if user is not None else None
            limit = ROLE_RATE_LIMITS.get(role, DEFAULT_RATE_LIMIT) if role else DEFAULT_RATE_LIMIT
            api_key_id = request.headers.get("X-API-Key", "")[:16] or client_ip
            if not self._check_limit(self._api_key_limits, api_key_id, limit):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please try again later."},
                    headers={"Retry-After": str(self.window_seconds)},
                )
        else:
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
