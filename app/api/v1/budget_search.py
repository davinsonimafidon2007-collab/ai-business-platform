"""Budget Search — Busca vehículos según capital total disponible."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agents.budget_search_agent import BudgetSearchAgent
from app.config.import_costs import get_profile, PROFILE_ALIASES

router = APIRouter(prefix="/budget-search", tags=["budget-search"])


class BudgetSearchRequest(BaseModel):
    total_budget: float = Field(..., gt=0, description="Capital total disponible (EUR)")
    profit_margin_min: float = Field(500.0, ge=0, description="Beneficio mínimo postventa (EUR)")
    profile: str = Field("SPAIN", description="Perfil de costes (SPAIN, GERMANY, etc.)")


class BudgetSearchResponse(BaseModel):
    total_budget: float
    max_purchase_price: float
    fixed_costs: float
    variable_buffer_pct: float
    status: str


@router.post("/search", response_model=BudgetSearchResponse)
async def search_by_budget(request: BudgetSearchRequest) -> Any:
    """Busca vehículos que encajen en el capital disponible."""
    profile_name = (request.profile or "SPAIN").upper()
    profile_name = PROFILE_ALIASES.get(profile_name, profile_name)

    try:
        profile = get_profile(profile_name)
    except KeyError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    agent = BudgetSearchAgent(profile_name=profile_name)
    max_price = agent.calculate_max_purchase_price(request.total_budget)

    fixed_costs = (
        profile.transport_cost
        + profile.registration_cost
        + profile.inspection_cost
        + profile.paperwork_cost
        + profile.miscellaneous_cost
    )

    variable_buffer = profile.tax_rate + profile.commission_rate + profile.repair_estimate_rate

    return BudgetSearchResponse(
        total_budget=request.total_budget,
        max_purchase_price=max_price,
        fixed_costs=round(fixed_costs, 2),
        variable_buffer_pct=round(variable_buffer * 100, 1),
        status="ok",
    )
