"""Search Orders API (PERSONAL.NOAUTH) — órdenes de búsqueda en background.

La búsqueda síncrona se mantiene para compatibilidad; las órdenes permiten
lanzar una búsqueda y que un job del scheduler la procese en segundo plano.
Cuando encuentra vehículos, el usuario ve el badge "X nuevos" y puede listarlos.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.budget_search_agent import BudgetSearchAgent
from app.config.import_costs import PROFILE_ALIASES, get_profile
from app.core.config import settings
from app.core.limits import MAX_LIST_DEPTH, MAX_SEARCH_RESULTS
from app.database import get_db_session
from app.dependencies.auth import get_current_user
from app.models.search_order import SearchOrder
from app.models.user import User
from app.repositories.search_order_repository import SearchOrderRepository

router = APIRouter(prefix="/search-orders", tags=["search-orders"])


# =============================================================================
# Schemas
# =============================================================================


class SearchOrderCreate(BaseModel):
    """Cuerpo para crear una orden de búsqueda en background."""

    query: str = Field(..., min_length=1, description="Término de búsqueda")
    total_budget: float | None = Field(
        None, gt=0, description="Capital total de la operación (EUR)"
    )
    profit_margin_min: float = Field(
        500.0, ge=0, description="Beneficio mínimo postventa (EUR)"
    )
    profile: str = Field("SPAIN", description="Perfil de costes de importación")
    filters: dict[str, Any] = Field(
        default_factory=dict,
        description="Filtros adicionales (brand, model, max_results, …)",
    )


class SearchOrderRead(BaseModel):
    """Orden de búsqueda (lista)."""

    id: str
    query: str
    total_budget: float | None = None
    max_purchase_price: float | None = None
    status: str
    results_count: int = 0
    new_count: int = 0
    error_message: str | None = None
    created_at: datetime
    last_run_at: datetime | None = None


class SearchOrderDetail(SearchOrderRead):
    """Orden con los vehículos encontrados."""

    vehicles: list[dict[str, Any]] = Field(default_factory=list)


class NewCountResponse(BaseModel):
    new_count: int = 0


# =============================================================================
# Helpers
# =============================================================================


def _order_read(order: SearchOrder) -> SearchOrderRead:
    return SearchOrderRead(
        id=order.id,
        query=order.query,
        total_budget=order.total_budget,
        max_purchase_price=order.max_purchase_price,
        status=order.status,
        results_count=order.results_count,
        new_count=order.new_count,
        error_message=order.error_message,
        created_at=order.created_at,
        last_run_at=order.last_run_at,
    )


def _parse_result_json(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, TypeError):
        return None


# =============================================================================
# Endpoints
# =============================================================================


@router.post("", response_model=SearchOrderRead, status_code=status.HTTP_201_CREATED)
async def create_search_order(
    request: SearchOrderCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> SearchOrderRead:
    """Crea una orden de búsqueda en background.

    Si ``total_budget`` viene, calcula el precio máximo de compra a partir del
    capital total (BudgetSearchAgent) y lo usa como ``budget_max``.
    """
    max_purchase_price: float | None = None
    if request.total_budget is not None:
        profile_name = (request.profile or "SPAIN").upper()
        profile_name = PROFILE_ALIASES.get(profile_name, profile_name)
        try:
            get_profile(profile_name)
        except KeyError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Perfil de costes desconocido: {request.profile}",
            ) from exc
        agent = BudgetSearchAgent(profile_name=profile_name)
        max_purchase_price = agent.calculate_max_purchase_price(request.total_budget)
        if max_purchase_price <= 0:
            profile_obj = get_profile(profile_name)
            fixed = (
                profile_obj.transport_cost
                + profile_obj.registration_cost
                + profile_obj.inspection_cost
                + profile_obj.paperwork_cost
                + profile_obj.miscellaneous_cost
            )
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Presupuesto insuficiente: {request.total_budget:.0f} € no cubre "
                    f"los costes fijos de importación ({fixed:.0f} €) del perfil "
                    f"'{profile_name}'. Sube el presupuesto o elige un perfil con "
                    f"costes fijos menores."
                ),
            )

    filters = dict(request.filters or {})
    filters.setdefault("max_results", 30)
    # P3: clamp max_results a [1, MAX_SEARCH_RESULTS] (los filtros son un dict
    # libre que no pasa por el validator de SearchRequest).
    try:
        max_results = int(filters["max_results"])
    except (TypeError, ValueError):
        max_results = 30
    filters["max_results"] = min(max(1, max_results), MAX_SEARCH_RESULTS)

    # P3: tope de órdenes activas por usuario (evita backlog/abuso del job).
    repo = SearchOrderRepository(session)
    max_pending = int(settings.search_order_max_pending_per_user or 0)
    if max_pending > 0:
        active = await repo.count_active_by_user(str(current_user.id))
        if active >= max_pending:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Ya tienes {active} búsquedas en curso (límite: {max_pending}). "
                    "Espera a que terminen o borra alguna antes de crear otra."
                ),
            )

    order = SearchOrder(
        user_id=str(current_user.id),
        query=request.query,
        total_budget=request.total_budget,
        max_purchase_price=max_purchase_price,
        filters=filters,
        status="PENDING",
        results_count=0,
        new_count=0,
    )
    saved = await repo.create(order)
    return _order_read(saved)


@router.get("", response_model=list[SearchOrderRead])
async def list_search_orders(
    skip: int = Query(0, ge=0, le=MAX_LIST_DEPTH),
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[SearchOrderRead]:
    repo = SearchOrderRepository(session)
    orders = await repo.list_by_user(str(current_user.id), skip=skip, limit=limit)
    return [_order_read(o) for o in orders]


@router.get("/new-count", response_model=NewCountResponse)
async def new_count(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> NewCountResponse:
    """Total de resultados sin ver en todas las órdenes (badge)."""
    repo = SearchOrderRepository(session)
    return NewCountResponse(new_count=await repo.total_new_by_user(str(current_user.id)))


@router.get("/{order_id}", response_model=SearchOrderDetail)
async def get_search_order(
    order_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> SearchOrderDetail:
    """Detalle de la orden con los vehículos encontrados (snapshots)."""
    repo = SearchOrderRepository(session)
    order = await repo.get_by_id(order_id, user_id=str(current_user.id))
    if order is None:
        raise HTTPException(status_code=404, detail="Orden de búsqueda no encontrada")

    vehicles: list[dict[str, Any]] = []
    links = await repo.list_order_vehicles(order.id)
    for link in links:
        item = _parse_result_json(link.result_json)
        vehicles.append(
            {
                "id": link.vehicle_id,
                "seen": link.seen,
                "result": item,
            }
        )

    base = _order_read(order).model_dump()
    return SearchOrderDetail(**base, vehicles=vehicles)


@router.post("/{order_id}/seen", response_model=SearchOrderRead)
async def mark_search_order_seen(
    order_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> SearchOrderRead:
    """Marca como vistos los resultados de la orden (resetea el badge)."""
    repo = SearchOrderRepository(session)
    order = await repo.get_by_id(order_id, user_id=str(current_user.id))
    if order is None:
        raise HTTPException(status_code=404, detail="Orden de búsqueda no encontrada")
    await repo.mark_seen(order_id, str(current_user.id))
    order.new_count = 0
    return _order_read(order)


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_search_order(
    order_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """Elimina una orden de búsqueda (no borra los vehículos)."""
    repo = SearchOrderRepository(session)
    order = await repo.get_by_id(order_id, user_id=str(current_user.id))
    if order is None:
        raise HTTPException(status_code=404, detail="Orden de búsqueda no encontrada")
    await repo.delete(order)
