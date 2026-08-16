"""HTTP admin endpoints for API keys (Task F.4).

Permite a un ADMIN (permiso `manage_api_keys`) listar y revocar
API keys de **cualquier** usuario. No toca el CRUD "own" de F.2
(`/api/v1/auth/api-keys`).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.v1.api_keys import ApiKeyNotFoundError, get_api_key_service
from app.dependencies.auth import require_manage_api_keys
from app.models.user import User
from app.schemas.api_key import ApiKeyListResponse, ApiKeyRead
from app.services.api_key_service import ApiKeyService

router = APIRouter(prefix="/admin/api-keys", tags=["Admin API Keys"])


@router.get("", response_model=ApiKeyListResponse)
async def admin_list_api_keys(
    user_id: str = Query(..., min_length=1, description="User ID whose keys to list"),
    active_only: bool = Query(True),
    service: ApiKeyService = Depends(get_api_key_service),
    _: User = Depends(require_manage_api_keys),
) -> ApiKeyListResponse:
    """List API key metadata for any user (ADMIN only)."""
    keys = await service.list_keys_for_user(user_id, active_only=active_only)
    items = [ApiKeyRead.model_validate(k) for k in keys]
    return ApiKeyListResponse(items=items, total=len(items))


@router.delete("/{api_key_id}", status_code=204)
async def admin_revoke_api_key(
    api_key_id: str,
    service: ApiKeyService = Depends(get_api_key_service),
    _: User = Depends(require_manage_api_keys),
) -> None:
    """Revoke any API key by id (ADMIN only).

    Devuelve 404 si la key no existe (mismo comportamiento que F.2).
    """
    record = await service.get_api_key_by_id(api_key_id)
    if record is None:
        raise ApiKeyNotFoundError()
    await service.deactivate_api_key(api_key_id)

