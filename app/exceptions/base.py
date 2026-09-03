from __future__ import annotations


class AppError(Exception):
    status_code: int = 500
    default_code: str = "internal_error"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        headers: dict[str, str] | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        self.message = message
        self.code = code or self.default_code
        self.headers = headers
        self.details = details
        super().__init__(message)


class UserAlreadyExistsError(AppError):
    status_code = 409
    default_code = "user_already_exists"


class UserNotFoundError(AppError):
    status_code = 404
    default_code = "user_not_found"


class InvalidCredentialsError(AppError):
    status_code = 401
    default_code = "invalid_credentials"


class AuthenticationError(AppError):
    status_code = 401
    default_code = "authentication_error"


class AuthorizationError(AppError):
    status_code = 403
    default_code = "authorization_error"


class VerificationTokenNotFoundError(AppError):
    status_code = 404
    default_code = "verification_token_not_found"


class VerificationTokenExpiredError(AppError):
    status_code = 400
    default_code = "verification_token_expired"


class PasswordResetTokenNotFoundError(AppError):
    status_code = 404
    default_code = "password_reset_token_not_found"


class PasswordResetTokenExpiredError(AppError):
    status_code = 400
    default_code = "password_reset_token_expired"


class PasswordResetError(AppError):
    status_code = 400
    default_code = "password_reset_error"


# ---------------------------------------------------------------------------
# Domain: Deals pipeline (replaces HTTPException leakage from services)
# ---------------------------------------------------------------------------

class DealNotFoundError(AppError):
    status_code = 404
    default_code = "not_found"


class DealConflictError(AppError):
    status_code = 409
    default_code = "conflict"

    def __init__(
        self,
        message: str,
        *,
        deal_id: str | None = None,
        code: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        details = {"deal_id": deal_id} if deal_id else None
        super().__init__(message, code=code, headers=headers, details=details)
        self.deal_id = deal_id


class DealValidationError(AppError):
    status_code = 422
    default_code = "deal_validation_error"


class DealConcurrentModificationError(AppError):
    status_code = 409
    default_code = "conflict"


# ---------------------------------------------------------------------------
# Domain: Opportunity phases
# ---------------------------------------------------------------------------

class PhaseNotFoundError(AppError):
    status_code = 404
    default_code = "phase_not_found"


class PhaseValidationError(AppError):
    status_code = 400
    default_code = "phase_validation_error"
