"""API endpoints for opportunities (Task C.1)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.opportunity import (
    OpportunityListResponse,
    OpportunityRead,
    OpportunityVehicleSummary,
)
from app.database import get_db_session
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.vehicle import Vehicle
from app.repositories.opportunity_repository import OpportunityRepository
from app.services.recommendation_labels import recommendation_label_es, risk_label_es

router = APIRouter(prefix="/opportunities", tags=["Opportunities"])


@router.get("", response_model=OpportunityListResponse)
async def list_opportunities(
    recommendation: str | None = Query(
        None, description="Filtro por recomendación (BUY_NOW, WATCH, NEGOTIATE, REJECT)"
    ),
    min_score: float | None = Query(None, ge=0, description="Score mínimo (0-100)"),
    min_roi: float | None = Query(None, description="ROI mínimo (%)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> OpportunityListResponse:
    """Lista oportunidades de importación del usuario autenticado.

    Devuelve oportunidades paginadas con score, profit, ROI, recomendación
    y resumen del vehículo asociado. Filtros opcionales por recomendación,
    score mínimo y ROI mínimo.
    """
    repo = OpportunityRepository(session)
    items, total = await repo.list_filtered(
        user_id=current_user.id,
        recommendation=recommendation,
        min_score=min_score,
        min_roi=min_roi,
        limit=limit,
        offset=offset,
    )

    # Cargar vehículos asociados para el resumen
    vehicle_ids = [opp.vehicle_id for opp in items]
    vehicles: dict[str, Vehicle] = {}
    if vehicle_ids:
        result = await session.execute(
            select(Vehicle).where(Vehicle.id.in_(vehicle_ids))
        )
        vehicles = {v.id: v for v in result.scalars().all()}

    mapped: list[OpportunityRead] = []
    for opp in items:
        vehicle = vehicles.get(opp.vehicle_id)
        vehicle_summary = None
        if vehicle is not None:
            vehicle_summary = OpportunityVehicleSummary(
                id=vehicle.id,
                brand=vehicle.brand,
                model=vehicle.model,
                year=vehicle.year,
                mileage=vehicle.mileage,
                price=vehicle.price,
                source=vehicle.source,
                external_id=vehicle.external_id,
                url=vehicle.url,
            )

        mapped.append(
            OpportunityRead(
                id=opp.id,
                vehicle=vehicle_summary,
                score=opp.opportunity_score,
                estimated_profit=opp.profit,
                roi_percentage=opp.roi,
                recommendation=opp.recommendation,
                risk_level=opp.risk,
                recommendation_label_es=recommendation_label_es(opp.recommendation),
                risk_label_es=risk_label_es(opp.risk),
                created_at=opp.created_at,
                updated_at=opp.analyzed_at,
            )
        )

    return OpportunityListResponse(
        items=mapped,
        total=total,
        limit=limit,
        offset=offset,
    )