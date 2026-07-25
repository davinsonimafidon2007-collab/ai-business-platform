from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserRead
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


async def get_auth_service(session: AsyncSession = Depends(get_db_session)) -> AuthService:
    repository = UserRepository(session)
    return AuthService(repository)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(payload: RegisterRequest, service: AuthService = Depends(get_auth_service)) -> UserRead:
    user = await service.register_user(email=str(payload.email), password=payload.password)
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login_user(payload: LoginRequest, service: AuthService = Depends(get_auth_service)) -> TokenResponse:
    user = await service.authenticate_user(email=str(payload.email), password=payload.password)
    token = service.create_access_token(user_id=user.id)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserRead)
async def get_current_user_profile(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current_user)
