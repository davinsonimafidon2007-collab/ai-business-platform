from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.exceptions import AppError
from app.middleware.request_id import get_request_id_from_state
from app.providers.exceptions import ProviderError
from app.schemas.error import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)

WWW_AUTHENTICATE_HEADER = {"WWW-Authenticate": "Bearer"}


def _get_request_id(request: Request) -> str | None:
    """Obtiene el request_id desde el estado de la request."""
    return get_request_id_from_state(request)


def _build_error_response(
    *,
    message: str,
    code: str,
    request_id: str | None = None,
    details: Any = None,
) -> dict[str, Any]:
    """Construye una respuesta de error estandarizada."""
    return ErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message,
            request_id=request_id,
            details=details,
        ),
    ).model_dump()


def _unauthorized_headers(headers: dict[str, str] | None) -> dict[str, str]:
    return headers or WWW_AUTHENTICATE_HEADER


# ---------------------------------------------------------------------------
# Handlers individuales
# ---------------------------------------------------------------------------


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    headers = exc.headers
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        headers = _unauthorized_headers(headers)

    return JSONResponse(
        status_code=exc.status_code,
        content=_build_error_response(
            message=exc.message,
            code=exc.code,
            request_id=_get_request_id(request),
        ),
        headers=headers,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    code = "http_error"

    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        code = "authentication_error"
    elif exc.status_code == status.HTTP_403_FORBIDDEN:
        code = "authorization_error"
    elif exc.status_code == status.HTTP_404_NOT_FOUND:
        code = "not_found"
    elif exc.status_code == status.HTTP_409_CONFLICT:
        code = "conflict"

    headers = exc.headers
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        headers = _unauthorized_headers(headers)

    return JSONResponse(
        status_code=exc.status_code,
        content=_build_error_response(
            message=detail,
            code=code,
            request_id=_get_request_id(request),
        ),
        headers=headers,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    first_error = errors[0] if errors else {}
    location = ".".join(str(part) for part in first_error.get("loc", ()))
    message = first_error.get("msg", "Validation error")
    detail = f"{location}: {message}" if location else message

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_build_error_response(
            message=detail,
            code="validation_error",
            request_id=_get_request_id(request),
            details=errors,
        ),
    )


async def provider_error_handler(request: Request, exc: ProviderError) -> JSONResponse:
    logger.warning(
        "Provider error: %s (provider=%s)",
        exc,
        getattr(exc, "provider", None),
    )

    provider_name = getattr(exc, "provider", None) or "unknown"
    message = str(exc) or f"Error from provider '{provider_name}'"

    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content=_build_error_response(
            message=message,
            code="provider_error",
            request_id=_get_request_id(request),
            details={"provider": provider_name},
        ),
    )


async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.exception("Database error: %s", exc)

    if settings.environment == "production":
        message = "A database error occurred."
    else:
        message = str(exc) or "A database error occurred."

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_build_error_response(
            message=message,
            code="database_error",
            request_id=_get_request_id(request),
        ),
    )


async def timeout_error_handler(request: Request, exc: TimeoutError) -> JSONResponse:
    logger.warning("Request timeout: %s", exc)

    return JSONResponse(
        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        content=_build_error_response(
            message="The request timed out.",
            code="timeout_error",
            request_id=_get_request_id(request),
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception: %s", exc)

    if settings.environment == "production":
        message = "An unexpected error occurred."
    else:
        message = str(exc) or "An unexpected error occurred."

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_build_error_response(
            message=message,
            code="internal_error",
            request_id=_get_request_id(request),
        ),
    )


# ---------------------------------------------------------------------------
# Registro en la aplicación
# ---------------------------------------------------------------------------


def register_exception_handlers(app: FastAPI) -> None:
    """Registra todos los manejadores de excepciones en la aplicación.

    El orden de registro es importante: los más específicos primero.
    """
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(ProviderError, provider_error_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)
    app.add_exception_handler(TimeoutError, timeout_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

