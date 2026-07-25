from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.exceptions import AppError
from app.schemas.error import ErrorResponse

logger = logging.getLogger(__name__)

WWW_AUTHENTICATE_HEADER = {"WWW-Authenticate": "Bearer"}


def _build_error_response(*, detail: str, code: str) -> dict[str, str]:
    return ErrorResponse(detail=detail, code=code).model_dump()


def _unauthorized_headers(headers: dict[str, str] | None) -> dict[str, str]:
    return headers or WWW_AUTHENTICATE_HEADER


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    headers = exc.headers
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        headers = _unauthorized_headers(headers)

    return JSONResponse(
        status_code=exc.status_code,
        content=_build_error_response(detail=exc.message, code=exc.code),
        headers=headers,
    )


async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
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
        content=_build_error_response(detail=detail, code=code),
        headers=headers,
    )


async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    first_error = errors[0] if errors else {}
    location = ".".join(str(part) for part in first_error.get("loc", ()))
    message = first_error.get("msg", "Validation error")
    detail = f"{location}: {message}" if location else message

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_build_error_response(detail=detail, code="validation_error"),
    )


async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception: %s", exc)

    if settings.environment == "production":
        detail = "An unexpected error occurred."
    else:
        detail = str(exc) or "An unexpected error occurred."

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_build_error_response(detail=detail, code="internal_error"),
    )


def register_exception_handlers(app: FastAPI) -> None:
    # Registrar manejadores en orden de especificidad
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
