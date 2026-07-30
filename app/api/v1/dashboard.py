from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.search_history import SearchHistory
from app.schemas.search_history import SearchHistoryRead

router = APIRouter(tags=["Dashboard"])


@router.get(
    "/dashboard/stats",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Estadísticas del dashboard",
    description="Devuelve estadísticas agregadas de búsquedas y oportunidades.",
)
async def get_dashboard_stats(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Obtiene estadísticas agregadas para el dashboard."""

    # Total de búsquedas
    total_searches_result = await session.execute(
        select(func.count(SearchHistory.id))
    )
    total_searches = total_searches_result.scalar() or 0

    # Búsquedas de los últimos 30 días
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    recent_searches_result = await session.execute(
        select(func.count(SearchHistory.id)).where(
            SearchHistory.timestamp >= thirty_days_ago
        )
    )
    recent_searches = recent_searches_result.scalar() or 0

    # Promedio de resultados por búsqueda
    avg_results_result = await session.execute(
        select(func.avg(SearchHistory.results_count)).where(
            SearchHistory.results_count.is_not(None)
        )
    )
    avg_results = avg_results_result.scalar() or 0.0

    # Promedio de tiempo de ejecución
    avg_time_result = await session.execute(
        select(func.avg(SearchHistory.execution_time)).where(
            SearchHistory.execution_time.is_not(None)
        )
    )
    avg_execution_time = avg_time_result.scalar() or 0.0

    # Búsquedas por proveedor (desde providers_used)
    # Nota: Esto es una simplificación, en producción se parsearía el JSON
    provider_stats: dict[str, int] = {}

    return {
        "total_searches": total_searches,
        "recent_searches": recent_searches,
        "average_results_per_search": round(avg_results, 1),
        "average_execution_time": round(avg_execution_time, 2),
        "provider_stats": provider_stats,
    }