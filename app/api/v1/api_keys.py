"""HTTP CRUD for user API keys (Task F.2).

Montado en /api/v1/auth/api-keys.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.dependencies.auth import get_current_user
from app.exceptions import AuthorizationError
from app.exceptions.base import AppError
from app.models.user import User
from app.repositories.api_key_repository import ApiKeyRepository
from app.schemas.api_key import (
    ApiKeyCreate,
    ApiKeyCreated,
    ApiKeyListResponse,
    ApiKeyRead,
)
from app.services.api_key_service import ApiKeyService
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/auth/api-keys", tags=["API Keys"])
_permission_service = PermissionService()


class ApiKeyNotFoundError(AppError):
    status_code = 404
    default_code = "api_key_not_found"

    def __init__(self, message: str = "API key not found") -> None:
        super().__init__(message)


async def get_api_key_service(
    session: AsyncSession = Depends(get_db_session),
) -> ApiKeyService:
    return ApiKeyService(ApiKeyRepository(session))


def _ensure_can_manage_own(user: User) -> None:
    role = user.role
    if _permission_service.can_manage_own_api_keys(role):
        return
    if _permission_service.can_manage_api_keys(role):
        return
    raise AuthorizationError("Insufficient permissions")


@router.post("", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    payload: ApiKeyCreate,
    service: ApiKeyService = Depends(get_api_key_service),
    current_user: User = Depends(get_current_user),
) -> ApiKeyCreated:
    _ensure_can_manage_own(current_user)
    record, full_key = await service.create_api_key(
        user_id=str(current_user.id),
        name=payload.name,
        scopes=payload.scopes,
        description=payload.description,
        expires_at=payload.expires_at,
    )
    base = ApiKeyRead.model_validate(record)
    return ApiKeyCreated(**base.model_dump(), api_key=full_key)


@router.get("", response_model=ApiKeyListResponse)
async def list_api_keys(
    service: ApiKeyService = Depends(get_api_key_service),
    current_user: User = Depends(get_current_user),
) -> ApiKeyListResponse:
    _ensure_can_manage_own(current_user)
    keys = await service.get_user_keys(str(current_user.id))
    items = [ApiKeyRead.model_validate(k) for k in keys]
    return ApiKeyListResponse(items=items, total=len(items))


@router.get("/{api_key_id}", response_model=ApiKeyRead)
async def get_api_key(
    api_key_id: str,
    service: ApiKeyService = Depends(get_api_key_service),
    current_user: User = Depends(get_current_user),
) -> ApiKeyRead:
    _ensure_can_manage_own(current_user)
    record = await service.get_api_key_by_id(api_key_id)
    if record is None or str(record.user_id) != str(current_user.id):
        raise ApiKeyNotFoundError()
    return ApiKeyRead.model_validate(record)


@router.delete("/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    api_key_id: str,
    service: ApiKeyService = Depends(get_api_key_service),
    current_user: User = Depends(get_current_user),
) -> None:
    _ensure_can_manage_own(current_user)
    record = await service.get_api_key_by_id(api_key_id)
    if record is None or str(record.user_id) != str(current_user.id):
        raise ApiKeyNotFoundError()
    await service.deactivate_api_key(api_key_id)
