from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.repositories.search_repository import SearchRepository
from app.schemas.search import SearchCreate, SearchRead, SearchUpdate
from app.services.search_service import SearchService

router = APIRouter(prefix="/searches", tags=["Searches"])


async def get_search_service(session: AsyncSession = Depends(get_db_session)) -> SearchService:
    repository = SearchRepository(session)
    return SearchService(repository)


@router.post("", response_model=SearchRead, status_code=status.HTTP_201_CREATED)
async def create_search(
    payload: SearchCreate,
    service: SearchService = Depends(get_search_service),
    current_user: User = Depends(get_current_user),
) -> SearchRead:
    search = await service.create_search(payload.model_dump())
    return SearchRead.model_validate(search)


@router.get("", response_model=list[SearchRead])
async def list_searches(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: SearchService = Depends(get_search_service),
    current_user: User = Depends(get_current_user),
) -> list[SearchRead]:
    searches = await service.list_searches(skip=skip, limit=limit)
    return [SearchRead.model_validate(s) for s in searches]


@router.get("/{search_id}", response_model=SearchRead)
async def get_search(
    search_id: str,
    service: SearchService = Depends(get_search_service),
    current_user: User = Depends(get_current_user),
) -> SearchRead:
    search = await service.get_search(search_id)
    if search is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Search not found")
    return SearchRead.model_validate(search)


@router.patch("/{search_id}", response_model=SearchRead)
async def update_search(
    search_id: str,
    payload: SearchUpdate,
    service: SearchService = Depends(get_search_service),
    current_user: User = Depends(get_current_user),
) -> SearchRead:
    search = await service.get_search(search_id)
    if search is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Search not found")
    updated = await service.update_search(search, payload.model_dump(exclude_unset=True))
    return SearchRead.model_validate(updated)


@router.delete("/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_search(
    search_id: str,
    service: SearchService = Depends(get_search_service),
    current_user: User = Depends(get_current_user),
) -> None:
    search = await service.get_search(search_id)
    if search is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Search not found")
    await service.delete_search(search)

