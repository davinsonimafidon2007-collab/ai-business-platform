from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.db.session import AsyncSessionLocal, get_db_session
from app.exceptions import UserAlreadyExistsError, UserNotFoundError
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


async def get_user_service(session: AsyncSession = Depends(get_db_session)) -> UserService:
    repository = UserRepository(session)
    return UserService(repository)


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, service: UserService = Depends(get_user_service)) -> UserRead:
    try:
        user = await service.create_user(email=str(payload.email), hashed_password=payload.hashed_password, full_name=payload.full_name)
    except UserAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return UserRead.model_validate(user)


@router.get("/", response_model=list[UserRead], status_code=status.HTTP_200_OK)
async def list_users(service: UserService = Depends(get_user_service)) -> list[UserRead]:
    users = await service.list_users()
    return [UserRead.model_validate(user) for user in users]


@router.get("/{user_id}", response_model=UserRead, status_code=status.HTTP_200_OK)
async def get_user(user_id: UUID, service: UserService = Depends(get_user_service)) -> UserRead:
    try:
        user = await service.get_user(user_id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return UserRead.model_validate(user)


@router.patch("/{user_id}", response_model=UserRead, status_code=status.HTTP_200_OK)
async def update_user(user_id: UUID, payload: UserUpdate, service: UserService = Depends(get_user_service)) -> UserRead:
    try:
        user = await service.update_user(user_id, **payload.model_dump(exclude_unset=True))
    except UserAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return UserRead.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: UUID, service: UserService = Depends(get_user_service)) -> None:
    try:
        await service.delete_user(user_id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
