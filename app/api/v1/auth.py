from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.dependencies.auth import get_current_user
from app.exceptions import AuthenticationError
from app.models.user import User
from app.notifications.email_provider import SmtpEmailProvider
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.password_reset_token_repository import PasswordResetTokenRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.repositories.verification_token_repository import VerificationTokenRepository
from app.schemas.auth import GoogleAuthRequest, LoginRequest, RegisterRequest, TokenResponse
from app.schemas.password_reset import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
)
from app.schemas.user import UserRead
from app.schemas.verification import VerificationRequestResponse, VerifyRequest, VerifyResponse
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.password_reset_service import PasswordResetService
from app.services.refresh_token_service import RefreshTokenService
from app.services.verification_service import VerificationService

router = APIRouter(prefix="/auth", tags=["Auth"])


async def get_auth_service(session: AsyncSession = Depends(get_db_session)) -> AuthService:
    repository = UserRepository(session)
    return AuthService(repository)


async def get_refresh_token_service(session: AsyncSession = Depends(get_db_session)) -> RefreshTokenService:
    repository = RefreshTokenRepository(session)
    return RefreshTokenService(repository)


async def get_audit_service(session: AsyncSession = Depends(get_db_session)) -> AuditService:
    repository = AuditLogRepository(session)
    return AuditService(repository)


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> UserRead:
    user = await service.register_user(email=str(payload.email), password=payload.password)
    await audit_service.log_user_created(user.id)
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login_user(
    request: Request,
    payload: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
    refresh_service: RefreshTokenService = Depends(get_refresh_token_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> TokenResponse:
    try:
        user = await auth_service.authenticate_user(email=str(payload.email), password=payload.password)
    except AuthenticationError:
        await audit_service.log_login_failed(
            email=str(payload.email), ip_address=_client_ip(request), user_agent=_user_agent(request)
        )
        raise

    access_token = auth_service.create_access_token(user_id=user.id)
    refresh_token = refresh_service.create_refresh_token(user_id=user.id)
    await refresh_service.create_refresh_token_record(user_id=user.id, token=refresh_token)
    await audit_service.log_login_success(
        user.id, ip_address=_client_ip(request), user_agent=_user_agent(request)
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/google", response_model=TokenResponse)
async def google_login(
    request: Request,
    payload: GoogleAuthRequest,
    auth_service: AuthService = Depends(get_auth_service),
    refresh_service: RefreshTokenService = Depends(get_refresh_token_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> TokenResponse:
    user = await auth_service.authenticate_with_google(id_token=payload.id_token)
    access_token = auth_service.create_access_token(user_id=user.id)
    refresh_token = refresh_service.create_refresh_token(user_id=user.id)
    await refresh_service.create_refresh_token_record(user_id=user.id, token=refresh_token)
    await audit_service.log_login_success(
        user.id, ip_address=_client_ip(request), user_agent=_user_agent(request)
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    request: Request,
    payload: dict[str, Any] = Body(...),
    auth_service: AuthService = Depends(get_auth_service),
    refresh_service: RefreshTokenService = Depends(get_refresh_token_service),
    audit_service: AuditService = Depends(get_audit_service),
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    refresh_token = payload.get("refresh_token")
    if not refresh_token:
        raise AuthenticationError("Refresh token is required")

    refresh_token_record = await refresh_service.validate_refresh_token(refresh_token)
    user_id = refresh_token_record.user_id

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if user is None or not user.is_active:
        await refresh_service.revoke_refresh_token(refresh_token)
        raise AuthenticationError("User is inactive")

    await refresh_service.revoke_refresh_token(refresh_token)
    new_access_token = auth_service.create_access_token(user_id=user_id)
    new_refresh_token = refresh_service.create_refresh_token(user_id=user_id)
    await refresh_service.create_refresh_token_record(user_id=user_id, token=new_refresh_token)
    await audit_service.log_refresh_token(
        user_id, ip_address=_client_ip(request), user_agent=_user_agent(request)
    )

    return TokenResponse(access_token=new_access_token, refresh_token=new_refresh_token)


@router.post("/logout")
async def logout(
    request: Request,
    payload: dict[str, Any] = Body(...),
    refresh_service: RefreshTokenService = Depends(get_refresh_token_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> dict[str, str]:
    refresh_token = payload.get("refresh_token")
    if refresh_token:
        try:
            decoded = refresh_service.decode_refresh_token(refresh_token)
            user_id = decoded.get("sub")
        except AuthenticationError:
            user_id = None
        await refresh_service.revoke_refresh_token(refresh_token)
        if user_id:
            await audit_service.log_logout(
                user_id, ip_address=_client_ip(request), user_agent=_user_agent(request)
            )
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserRead)
async def get_current_user_profile(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current_user)


async def get_verification_service(session: AsyncSession = Depends(get_db_session)) -> VerificationService:
    user_repository = UserRepository(session)
    token_repository = VerificationTokenRepository(session)
    email_provider = SmtpEmailProvider()
    return VerificationService(
        user_repository=user_repository,
        token_repository=token_repository,
        email_provider=email_provider,
    )


@router.post("/request-verification", response_model=VerificationRequestResponse)
async def request_verification(
    current_user: User = Depends(get_current_user),
    verification_service: VerificationService = Depends(get_verification_service),
) -> VerificationRequestResponse:
    await verification_service.request_verification(current_user)
    return VerificationRequestResponse()


@router.post("/verify", response_model=VerifyResponse)
async def verify_email(
    payload: VerifyRequest,
    verification_service: VerificationService = Depends(get_verification_service),
) -> VerifyResponse:
    await verification_service.confirm_verification(payload.token)
    return VerifyResponse()


# ---------------------------------------------------------------------------
# Password Reset
# ---------------------------------------------------------------------------


async def get_password_reset_service(session: AsyncSession = Depends(get_db_session)) -> PasswordResetService:
    user_repository = UserRepository(session)
    token_repository = PasswordResetTokenRepository(session)
    email_provider = SmtpEmailProvider()
    return PasswordResetService(
        user_repository=user_repository,
        token_repository=token_repository,
        email_provider=email_provider,
    )


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    payload: ForgotPasswordRequest,
    password_reset_service: PasswordResetService = Depends(get_password_reset_service),
) -> ForgotPasswordResponse:
    await password_reset_service.request_password_reset(str(payload.email))
    return ForgotPasswordResponse()


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(
    request: Request,
    payload: ResetPasswordRequest,
    password_reset_service: PasswordResetService = Depends(get_password_reset_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> ResetPasswordResponse:
    user_id = await password_reset_service.reset_password(payload.token, payload.new_password)
    await audit_service.log_password_changed(user_id, ip_address=_client_ip(request))
    return ResetPasswordResponse()
