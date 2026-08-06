from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_audit_service
from app.database import get_db_session
from app.dependencies.auth import get_current_user, require_admin, require_permission
from app.models.role import Role
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserRead, UserRoleUpdate, UserUpdate
from app.services.audit_service import AuditService
from app.services.auth_service import password_hasher
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


async def get_user_service(session: AsyncSession = Depends(get_db_session)) -> UserService:
    repository = UserRepository(session)
    return UserService(repository)


def _ensure_self_or_admin(user_id: str, current_user: User) -> None:
    """Permite la operación solo si es el propio usuario o un admin."""
    if str(current_user.id) != str(user_id) and current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para acceder a este usuario",
        )


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    service: UserService = Depends(get_user_service),
    audit_service: AuditService = Depends(get_audit_service),
    current_user: User = Depends(require_permission("manage_users")),
) -> UserRead:
    """Solo un admin puede crear usuarios por esta vía (el alta normal es /auth/register)."""
    hashed = password_hasher.hash(payload.password)
    user = await service.create_user(
        email=str(payload.email),
        hashed_password=hashed,
        full_name=payload.full_name,
    )
    await audit_service.log_user_created(user.id, admin_user_id=current_user.id)
    return UserRead.model_validate(user)


@router.get("/", response_model=list[UserRead], status_code=status.HTTP_200_OK)
async def list_users(
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_permission("manage_users")),
) -> list[UserRead]:
    users = await service.list_users()
    return [UserRead.model_validate(user) for user in users]


@router.get("/{user_id}", response_model=UserRead, status_code=status.HTTP_200_OK)
async def get_user(
    user_id: UUID,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user),
) -> UserRead:
    _ensure_self_or_admin(str(user_id), current_user)
    user = await service.get_user(user_id)
    return UserRead.model_validate(user)


@router.patch("/{user_id}", response_model=UserRead, status_code=status.HTTP_200_OK)
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user),
) -> UserRead:
    _ensure_self_or_admin(str(user_id), current_user)
    data = payload.model_dump(exclude_unset=True)

    if "is_active" in data and current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un administrador puede cambiar is_active",
        )

    user = await service.update_user(user_id, **data)
    return UserRead.model_validate(user)


@router.patch("/{user_id}/role", response_model=UserRead, status_code=status.HTTP_200_OK)
async def update_user_role(
    user_id: UUID,
    payload: UserRoleUpdate,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_permission("manage_roles")),
) -> UserRead:
    """Solo quien tenga manage_roles (ADMIN) puede cambiar el rol de un usuario."""
    if str(current_user.id) == str(user_id) and payload.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes quitarte el rol admin a ti mismo",
        )

    user = await service.update_user_role(user_id, payload.role)
    return UserRead.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    service: UserService = Depends(get_user_service),
    audit_service: AuditService = Depends(get_audit_service),
    current_user: User = Depends(require_permission("manage_users")),
) -> None:
    await service.delete_user(user_id)
    await audit_service.log_user_deleted(str(user_id), admin_user_id=current_user.id)
