"""Budget Search — Busca vehículos según capital total disponible."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.agents.base import AgentError, AgentExecutionError, AgentTimeoutError
from app.agents.budget_search_agent import BudgetSearchAgent
from app.agents.schemas import BudgetSearchAgentInput
from app.api.v1.dependencies import get_budget_search_agent, get_search_engine_service
from app.api.v1.routes.search import _build_search_result_item
from app.api.v1.schemas.search import ProviderIssueSchema, SearchResultItem
from app.config.import_costs import PROFILE_ALIASES, get_profile
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services.provider_issue_labels import build_provider_issue_payloads
from app.services.search_engine import SearchEngineService

router = APIRouter(prefix="/budget-search", tags=["budget-search"])


class BudgetSearchRequest(BaseModel):
    total_budget: float = Field(..., gt=0, description="Capital total disponible (EUR)")
    profit_margin_min: float = Field(500.0, ge=0, description="Beneficio mínimo postventa (EUR)")
    profile: str = Field("SPAIN", description="Perfil de costes (SPAIN, GERMANY, etc.)")
    query: str = Field("*", min_length=1, description="Término de búsqueda")
    max_results: int = Field(30, ge=1, le=100, description="Máximo de resultados a devolver")


class BudgetSearchResponse(BaseModel):
    total_budget: float
    max_purchase_price: float
    fixed_costs: float
    variable_buffer_pct: float
    status: str
    query: str = "*"
    results: list[SearchResultItem] = Field(default_factory=list)
    provider_issues: list[ProviderIssueSchema] = Field(default_factory=list)
    filtered_out_count: int = Field(
        0, ge=0, description="Resultados descartados por profit_margin_min"
    )


@router.post("/search", response_model=BudgetSearchResponse)
async def search_by_budget(
    request: BudgetSearchRequest,
    search_engine: SearchEngineService = Depends(get_search_engine_service),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Busca vehículos que encajen en el capital disponible.

    Calcula el precio máximo de compra a partir del capital total y ejecuta
    una búsqueda real con ese tope como ``budget_max``, filtrando los
    resultados por beneficio neto mínimo.
    """
    profile_name = (request.profile or "SPAIN").upper()
    profile_name = PROFILE_ALIASES.get(profile_name, profile_name)

    try:
        profile = get_profile(profile_name)
    except KeyError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    fixed_costs = (
        profile.transport_cost
        + profile.registration_cost
        + profile.inspection_cost
        + profile.paperwork_cost
        + profile.miscellaneous_cost
    )
    variable_buffer = profile.tax_rate + profile.commission_rate + profile.repair_estimate_rate

    agent = BudgetSearchAgent(profile_name=profile_name, search_engine=search_engine)
    try:
        result = await agent.run(
            BudgetSearchAgentInput(
                total_budget=request.total_budget,
                query=request.query,
                max_results=request.max_results,
                profit_margin_min=request.profit_margin_min,
            )
        )
    except AgentTimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except AgentExecutionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except AgentError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if result.status == "budget_too_low":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Presupuesto insuficiente: {request.total_budget:.0f} € no cubre "
                f"los costes fijos de importación del perfil '{profile_name}'. "
                f"Sin ese margen no puede comprarse ningún vehículo."
            ),
        )

    items = [_build_search_result_item(r) for r in result.results]
    return BudgetSearchResponse(
        total_budget=result.total_budget,
        max_purchase_price=result.max_purchase_price,
        fixed_costs=round(fixed_costs, 2),
        variable_buffer_pct=round(variable_buffer * 100, 1),
        status=result.status,
        query=result.query,
        results=items,
        provider_issues=[
            ProviderIssueSchema(**payload)
            for payload in build_provider_issue_payloads(result.provider_issues)
        ],
        filtered_out_count=result.filtered_out_count,
    )
