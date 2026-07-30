from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.search import Search
from app.models.vehicle import Vehicle
from app.models.inspection import InspectionSession
from app.models.opportunity import Opportunity

router = APIRouter(tags=["Dashboard"])


@router.get(
    "/dashboard/stats",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Estadísticas del dashboard",
    description="Devuelve estadísticas agregadas del usuario autenticado.",
)
async def get_dashboard_stats(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Obtiene estadísticas agregadas del usuario autenticado (no globales)."""
    user_id = current_user.id
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

    # --- Búsquedas guardadas por el usuario ---
    total_searches_result = await session.execute(
        select(func.count(Search.id)).where(Search.user_id == user_id)
    )
    total_searches = total_searches_result.scalar() or 0

    recent_searches_result = await session.execute(
        select(func.count(Search.id)).where(
            Search.user_id == user_id, Search.created_at >= thirty_days_ago
        )
    )
    recent_searches = recent_searches_result.scalar() or 0

    # --- Vehículos del usuario ---
    total_vehicles_result = await session.execute(
        select(func.count(Vehicle.id)).where(Vehicle.user_id == user_id)
    )
    total_vehicles = total_vehicles_result.scalar() or 0

    # --- Inspecciones del usuario ---
    total_inspections_result = await session.execute(
        select(func.count(InspectionSession.id)).where(
            InspectionSession.user_id == user_id
        )
    )
    total_inspections = total_inspections_result.scalar() or 0

    completed_inspections_result = await session.execute(
        select(func.count(InspectionSession.id)).where(
            InspectionSession.user_id == user_id,
            InspectionSession.status == "COMPLETED",
        )
    )
    completed_inspections = completed_inspections_result.scalar() or 0

    # --- Oportunidades sobre vehículos del usuario (join vía vehicle.user_id) ---
    total_opportunities_result = await session.execute(
        select(func.count(Opportunity.id))
        .join(Vehicle, Vehicle.id == Opportunity.vehicle_id)
        .where(Vehicle.user_id == user_id)
    )
    total_opportunities = total_opportunities_result.scalar() or 0

    return {
        "total_searches": total_searches,
        "recent_searches": recent_searches,
        "total_vehicles": total_vehicles,
        "total_inspections": total_inspections,
        "completed_inspections": completed_inspections,
        "total_opportunities": total_opportunities,
    }