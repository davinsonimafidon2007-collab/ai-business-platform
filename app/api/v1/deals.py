"""API endpoints for deals pipeline (Task D.1)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.deal import (
    DealCreate,
    DealListResponse,
    DealRead,
    DealSimulationUpdate,
    DealUpdateStatus,
)
from app.database import get_db_session
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.repositories.deal_repository import DealRepository
from app.repositories.vehicle_repository import VehicleRepository
from app.services.deal_service import DealService

router = APIRouter(prefix="/deals", tags=["Deals"])


async def get_deal_service(
    session: AsyncSession = Depends(get_db_session),
) -> DealService:
    """Obtiene el servicio de deals con su repositorio."""
    return DealService(DealRepository(session))


@router.post("", response_model=DealRead, status_code=status.HTTP_201_CREATED)
async def create_deal(
    payload: DealCreate,
    session: AsyncSession = Depends(get_db_session),
    service: DealService = Depends(get_deal_service),
    current_user: User = Depends(get_current_user),
) -> DealRead:
    """Crea un nuevo deal en estado NEW."""
    vehicle_id = payload.vehicle_id
    if vehicle_id is None and payload.source and payload.external_id:
        vehicle_repository = VehicleRepository(session)
        vehicle = await vehicle_repository.get_by_external_id(
            source=payload.source,
            external_id=payload.external_id,
            user_id=str(current_user.id),
        )
        if vehicle is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vehicle not found for source={payload.source}, external_id={payload.external_id}",
            )
        vehicle_id = vehicle.id
    deal = await service.create(
        user_id=current_user.id,
        opportunity_id=payload.opportunity_id,
        vehicle_id=vehicle_id,
        notes=payload.notes,
        contact_channel=payload.contact_channel,
    )
    return DealRead.model_validate(deal)


@router.get("", response_model=DealListResponse)
async def list_deals(
    deal_status: str | None = Query(
        None, alias="status", description="Filtro por estado (NEW, CONTACTED, ...)"
    ),
    opportunity_id: str | None = Query(
        None,
        description="Filtro por oportunidad (deals vinculados a esa oportunidad)",
    ),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: DealService = Depends(get_deal_service),
    current_user: User = Depends(get_current_user),
) -> DealListResponse:
    """Lista deals del usuario autenticado (solo los suyos)."""
    items, total = await service.list(
        user_id=current_user.id,
        deal_status=deal_status,
        opportunity_id=opportunity_id,
        limit=limit,
        offset=offset,
    )
    return DealListResponse(
        items=[DealRead.model_validate(d) for d in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{deal_id}", response_model=DealRead)
async def get_deal(
    deal_id: str,
    service: DealService = Depends(get_deal_service),
    current_user: User = Depends(get_current_user),
) -> DealRead:
    """Obtiene un deal del usuario (404 si no existe o es ajeno)."""
    deal = await service.get(deal_id, current_user.id)
    return DealRead.model_validate(deal)


@router.patch("/{deal_id}/status", response_model=DealRead)
async def update_deal_status(
    deal_id: str,
    payload: DealUpdateStatus,
    service: DealService = Depends(get_deal_service),
    current_user: User = Depends(get_current_user),
) -> DealRead:
    """Transiciona un deal a un nuevo estado del pipeline."""
    deal = await service.transition(
        deal_id=deal_id,
        user_id=current_user.id,
        new_status=payload.status,
        notes=payload.notes,
        offer_price=payload.offer_price,
    )
    return DealRead.model_validate(deal)


@router.patch("/{deal_id}/simulation", response_model=DealRead)
async def update_deal_simulation(
    deal_id: str,
    payload: DealSimulationUpdate,
    service: DealService = Depends(get_deal_service),
    current_user: User = Depends(get_current_user),
) -> DealRead:
    """Guarda la última simulación de margen en un deal (Task E.2).

    Actualiza solo los campos ``last_sim_*``; no cambia el estado del
    pipeline ni los campos de negociación. Ownership igual que el resto.
    """
    deal = await service.save_simulation(
        deal_id=deal_id,
        user_id=current_user.id,
        purchase_price=payload.purchase_price,
        estimated_sale_price=payload.estimated_sale_price,
        total_cost=payload.total_cost,
        net_profit=payload.net_profit,
        roi_percentage=payload.roi_percentage,
        profile_name=payload.profile_name,
    )
    return DealRead.model_validate(deal)


@router.delete("/{deal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deal(
    deal_id: str,
    service: DealService = Depends(get_deal_service),
    current_user: User = Depends(get_current_user),
) -> None:
    """Elimina un deal propio (TASK-021). 404 si no existe o es ajeno."""
    await service.delete(deal_id, current_user.id)
