"""Admin feature flags endpoints — TASK-012.

CRUD de feature flags + invalidación de cache.
Protegido por ``require_admin`` (igual que el resto de rutas admin).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies.auth import require_admin
from app.models.user import User
from app.schemas.feature_flag import (
    FeatureFlagCreate,
    FeatureFlagRead,
    FeatureFlagUpdate,
)
from app.services.feature_flag_service import FeatureFlagService

router = APIRouter(prefix="/admin/feature-flags", tags=["admin-feature-flags"])


@router.get("", response_model=list[FeatureFlagRead])
async def list_feature_flags(
    _: User = Depends(require_admin),
) -> list[FeatureFlagRead]:
    flags = await FeatureFlagService.list_flags()
    return [FeatureFlagRead.model_validate(f) for f in flags]


@router.post("", response_model=FeatureFlagRead)
async def create_feature_flag(
    payload: FeatureFlagCreate,
    _: User = Depends(require_admin),
) -> FeatureFlagRead:
    flag = await FeatureFlagService.set_flag(
        key=payload.key,
        value=payload.value,
        description=payload.description,
    )
    return FeatureFlagRead.model_validate(flag)


@router.patch("/{key}", response_model=FeatureFlagRead)
async def update_feature_flag(
    key: str,
    payload: FeatureFlagUpdate,
    _: User = Depends(require_admin),
) -> FeatureFlagRead:
    flag = await FeatureFlagService.set_flag(
        key=key,
        value=payload.value,
        description=payload.description,
    )
    return FeatureFlagRead.model_validate(flag)


@router.delete("/{key}")
async def delete_feature_flag(
    key: str,
    _: User = Depends(require_admin),
) -> dict:
    existed = await FeatureFlagService.delete_flag(key)
    if not existed:
        raise HTTPException(status_code=404, detail="Feature flag not found")
    return {"detail": "Feature flag deleted"}