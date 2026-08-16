from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.dependencies.auth import get_current_user
from app.models.inspection import InspectionSession
from app.models.opportunity import Opportunity
from app.models.search import Search
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.vehicle_evaluation import VehicleEvaluation
from app.repositories.search_order_repository import SearchOrderRepository

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
    thirty_days_ago = datetime.now(UTC) - timedelta(days=30)

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

    # --- Promedios de búsquedas (solo sobre las que tienen datos) ---
    avg_results_result = await session.execute(
        select(func.avg(Search.results_count)).where(
            Search.user_id == user_id, Search.results_count.is_not(None)
        )
    )
    average_results_per_search = avg_results_result.scalar() or 0

    avg_time_result = await session.execute(
        select(func.avg(Search.execution_time)).where(
            Search.user_id == user_id, Search.execution_time.is_not(None)
        )
    )
    average_execution_time = avg_time_result.scalar() or 0

    # --- Órdenes de búsqueda (badge de nuevos + últimas órdenes) ---
    order_repo = SearchOrderRepository(session)
    new_search_results = await order_repo.total_new_by_user(str(user_id))
    recent_orders_raw = await order_repo.list_by_user(str(user_id), limit=5)
    recent_orders = [
        {
            "id": order.id,
            "query": order.query,
            "status": order.status,
            "results_count": order.results_count,
            "new_count": order.new_count,
            "max_purchase_price": order.max_purchase_price,
            "error_message": order.error_message,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "last_run_at": order.last_run_at.isoformat() if order.last_run_at else None,
        }
        for order in recent_orders_raw
    ]

    # --- Últimos vehículos guardados con su evaluación (si existe) ---
    vehicles_stmt = (
        select(Vehicle, VehicleEvaluation)
        .outerjoin(VehicleEvaluation, VehicleEvaluation.vehicle_id == Vehicle.id)
        .where(Vehicle.user_id == user_id)
        .order_by(Vehicle.created_at.desc())
        .limit(6)
    )
    recent_vehicles_rows = (await session.execute(vehicles_stmt)).all()
    recent_vehicles = []
    for vehicle, evaluation in recent_vehicles_rows:
        # CRIT.004: la columna es JSON (lista) desde la migración k3l4m5n6o7p8.
        # Soportar legacy string (CSV) por si una fila quedó sin migrar.
        raw_images = vehicle.images
        if isinstance(raw_images, list):
            images = [str(i) for i in raw_images if i]
        elif isinstance(raw_images, str):
            images = [i.strip() for i in raw_images.split(",") if i.strip()]
        else:
            images = []
        recent_vehicles.append(
            {
                "id": vehicle.id,
                "brand": vehicle.brand,
                "model": vehicle.model,
                "year": vehicle.year,
                "price": vehicle.price,
                "currency": vehicle.currency,
                "image_url": images[0] if images else None,
                "score": evaluation.score if evaluation else None,
                "classification": evaluation.classification if evaluation else None,
                "estimated_profit": (
                    evaluation.estimated_profit if evaluation else None
                ),
                "estimated_total_cost": (
                    evaluation.estimated_total_cost if evaluation else None
                ),
                "has_evaluation": evaluation is not None,
                "created_at": vehicle.created_at.isoformat()
                if vehicle.created_at
                else None,
            }
        )

    return {
        "total_searches": total_searches,
        "recent_searches": recent_searches,
        "total_vehicles": total_vehicles,
        "total_inspections": total_inspections,
        "completed_inspections": completed_inspections,
        "total_opportunities": total_opportunities,
        "average_results_per_search": round(float(average_results_per_search), 2),
        "average_execution_time": round(float(average_execution_time), 2),
        "new_search_results": new_search_results,
        "recent_orders": recent_orders,
        "recent_vehicles": recent_vehicles,
    }
