from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db_session
from app.dependencies.auth import get_current_user
from app.exceptions import AuthenticationError
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.notifications.email_provider import SmtpEmailProvider
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


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(payload: RegisterRequest, service: AuthService = Depends(get_auth_service)) -> UserRead:
    user = await service.register_user(email=str(payload.email), password=payload.password)
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login_user(
    request: Request,
    payload: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
    refresh_service: RefreshTokenService = Depends(get_refresh_token_service),
) -> TokenResponse:
    user = await auth_service.authenticate_user(email=str(payload.email), password=payload.password)
    access_token = auth_service.create_access_token(user_id=user.id)
    refresh_token = refresh_service.create_refresh_token(user_id=user.id)
    await refresh_service.create_refresh_token_record(user_id=user.id, token=refresh_token)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/google", response_model=TokenResponse)
async def google_login(
    payload: GoogleAuthRequest,
    auth_service: AuthService = Depends(get_auth_service),
    refresh_service: RefreshTokenService = Depends(get_refresh_token_service),
) -> TokenResponse:
    user = await auth_service.authenticate_with_google(id_token=payload.id_token)
    access_token = auth_service.create_access_token(user_id=user.id)
    refresh_token = refresh_service.create_refresh_token(user_id=user.id)
    await refresh_service.create_refresh_token_record(user_id=user.id, token=refresh_token)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    payload: dict[str, Any] = Body(...),
    auth_service: AuthService = Depends(get_auth_service),
    refresh_service: RefreshTokenService = Depends(get_refresh_token_service),
) -> TokenResponse:
    refresh_token = payload.get("refresh_token")
    if not refresh_token:
        raise AuthenticationError("Refresh token is required")
    
    refresh_token_record = await refresh_service.validate_refresh_token(refresh_token)
    user_id = refresh_token_record.user_id
    
    # Rotación: revocar el refresh token usado y crear uno nuevo
    await refresh_service.revoke_refresh_token(refresh_token)
    new_access_token = auth_service.create_access_token(user_id=user_id)
    new_refresh_token = refresh_service.create_refresh_token(user_id=user_id)
    await refresh_service.create_refresh_token_record(user_id=user_id, token=new_refresh_token)
    
    return TokenResponse(access_token=new_access_token, refresh_token=new_refresh_token)


@router.post("/logout")
async def logout(
    payload: dict[str, Any] = Body(...),
    refresh_service: RefreshTokenService = Depends(get_refresh_token_service),
) -> dict[str, str]:
    refresh_token = payload.get("refresh_token")
    if refresh_token:
        await refresh_service.revoke_refresh_token(refresh_token)
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
    payload: ResetPasswordRequest,
    password_reset_service: PasswordResetService = Depends(get_password_reset_service),
) -> ResetPasswordResponse:
    await password_reset_service.reset_password(payload.token, payload.new_password)
    return ResetPasswordResponse()