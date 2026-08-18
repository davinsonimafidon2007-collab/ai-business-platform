from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from app.core.config import settings


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce HTTPS in non-development environments.

    Redirects HTTP requests to HTTPS (301 Moved Permanently) when
    `settings.https_redirect` is True or in production environments
    where `x-forwarded-proto` is not 'https'.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        should_redirect = settings.https_redirect or (
            settings.environment == "production" and settings.https_redirect
        )
        if should_redirect:
            proto = request.headers.get("x-forwarded-proto", request.url.scheme)
            if proto != "https":
                url = str(request.url).replace("http://", "https://", 1)
                return RedirectResponse(url, status_code=301)
        return await call_next(request)
