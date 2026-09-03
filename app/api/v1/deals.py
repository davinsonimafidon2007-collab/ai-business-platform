"""API endpoints for deals pipeline (Task D.1 / state machine v2)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.deal import (
    DealCreate,
    DealHistoryResponse,
    DealListResponse,
    DealRead,
    DealSimulationUpdate,
    DealStatusHistoryEntry,
    DealUpdateStatus,
)
from app.database import get_db_session
from app.dependencies.auth import get_current_user
from app.models.deal import DealStatus
from app.models.user import User
from app.repositories.deal_repository import DealRepository
from app.repositories.vehicle_evaluation_repository import VehicleEvaluationRepository
from app.repositories.vehicle_repository import VehicleRepository
from app.services.deal_service import DealService

router = APIRouter(prefix="/deals", tags=["Deals"])


async def get_deal_service(
    session: AsyncSession = Depends(get_db_session),
) -> DealService:
    """Obtiene el servicio de deals con su repositorio."""
    return DealService(
        DealRepository(session), VehicleEvaluationRepository(session)
    )


def _parse_status_filter(value: str | None) -> DealStatus | None:
    """Convierte el query param ``status`` a DealStatus (422 si es inválido)."""
    if value is None:
        return None
    try:
        return DealStatus(value.strip().upper())
    except ValueError:
        allowed = [s.value for s in DealStatus]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid status filter. Allowed values: {allowed}",
        ) from None


@router.post("", response_model=DealRead, status_code=status.HTTP_201_CREATED)
async def create_deal(
    payload: DealCreate,
    session: AsyncSession = Depends(get_db_session),
    service: DealService = Depends(get_deal_service),
    current_user: User = Depends(get_current_user),
) -> DealRead:
    """Crea un nuevo deal en estado NEW.

    Idempotente frente a duplicados: solo puede existir UN deal activo por
    oportunidad y usuario (409 en caso contrario), garantizado tanto a nivel
    de servicio como por índice único parcial en BD.
    """
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
        None, alias="status", description="Filtro por estado (NEW, ANALYZING, ...)"
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
        deal_status=_parse_status_filter(deal_status),
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


@router.get("/{deal_id}/history", response_model=DealHistoryResponse)
async def get_deal_history(
    deal_id: str,
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: DealService = Depends(get_deal_service),
    current_user: User = Depends(get_current_user),
) -> DealHistoryResponse:
    """Historial de estados de un deal propio (auditoría de transiciones).

    Cada cambio de estado queda registrado de forma inmutable: estado origen,
    estado destino, usuario, notas, precio de oferta y fecha.
    """
    items, total = await service.get_history(
        deal_id,
        current_user.id,
        limit=limit,
        offset=offset,
    )
    return DealHistoryResponse(
        items=[DealStatusHistoryEntry.model_validate(h) for h in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.patch("/{deal_id}/status", response_model=DealRead)
async def update_deal_status(
    deal_id: str,
    payload: DealUpdateStatus,
    service: DealService = Depends(get_deal_service),
    current_user: User = Depends(get_current_user),
) -> DealRead:
    """Transiciona un deal a un nuevo estado del pipeline.

    - Transición inválida según la máquina de estados -> 422.
    - Mismo estado actual -> 200 idempotente (no-op).
    - Escritura concurrente perdida -> 409.
    - Los campos de cumplimiento (TASK 3) solo se aplican cuando ``status``
      es la etapa correspondiente (BOUGHT/IN_TRANSIT/REGISTERED/SOLD); se
      ignoran en cualquier otra transición.
    """
    deal = await service.transition(
        deal_id=deal_id,
        user_id=current_user.id,
        new_status=payload.status,
        notes=payload.notes,
        offer_price=payload.offer_price,
        actual_purchase_price=payload.actual_purchase_price,
        transport_carrier=payload.transport_carrier,
        transport_cost=payload.transport_cost,
        registration_plate=payload.registration_plate,
        registration_cost=payload.registration_cost,
        sale_price=payload.sale_price,
        buyer_name=payload.buyer_name,
        buyer_contact=payload.buyer_contact,
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
