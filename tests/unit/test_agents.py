"""Tests de los agents de dominio con services reales (AUDIT.AGENTS.1).

No se mockea la lógica de negocio: ScoringAgent/OpportunityAgent/NegotiationAgent/
AlertAgent ejecutan sus services reales. Solo el motor de búsqueda (I/O externo)
se sustituye por un fake determinista.
"""

from __future__ import annotations

import pytest

from app.agents.alert_agent import AlertAgent
from app.agents.base import AgentValidationError
from app.agents.budget_search_agent import BudgetSearchAgent
from app.agents.negotiation_agent import NegotiationAgent
from app.agents.opportunity_agent import OpportunityAgent
from app.agents.schemas import (
    AlertAgentInput,
    AlertOpportunityInput,
    AlertRulesInput,
    NegotiationAgentInput,
    OpportunityAgentInput,
    RescoreAgentInput,
    ScoringAgentInput,
)
from app.agents.scoring_agent import ScoringAgent
from app.models.search import SearchEngineResult, SearchResult, SearchSummary

# =============================================================================
# ScoringAgent
# =============================================================================


@pytest.mark.asyncio
async def test_scoring_agent_scores_real_vehicle_data():
    agent = ScoringAgent()

    output = await agent.run(
        ScoringAgentInput(
            vehicle={
                "price": 10000,
                "mileage": 50000,
                "year": 2019,
                "fuel_type": "diesel",
                "description": "x" * 200,
            }
        )
    )

    assert 0 < output.score <= 100
    assert output.category_key in ("excellent", "very_good", "good", "acceptable", "poor")
    assert output.category_label_es


@pytest.mark.asyncio
async def test_scoring_agent_rejects_invalid_input():
    agent = ScoringAgent()

    with pytest.raises(AgentValidationError):
        await agent.run({"vehicle": {"mileage": -5}})


@pytest.mark.asyncio
async def test_scoring_agent_rescore_computes_delta():
    agent = ScoringAgent()

    result = await agent.rescore(
        {
            "vehicle_id": "veh-1",
            "new_price": 8000,
            "vehicle": {"price": 10000, "mileage": 50000, "year": 2019},
        }
    )

    assert result.vehicle_id == "veh-1"
    assert result.new_price == 8000
    assert 0 < result.score <= 100
    assert 0 < result.previous_score <= 100
    # Bajar el precio nunca debe empeorar el score en este escenario simple.
    assert result.delta == float(result.score - result.previous_score)


def test_rescore_input_requires_positive_price():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        RescoreAgentInput(vehicle_id="v", new_price=0, vehicle={"price": 100})


# =============================================================================
# OpportunityAgent
# =============================================================================


@pytest.mark.asyncio
async def test_opportunity_agent_returns_full_analysis_and_rejects_bad_deal():
    agent = OpportunityAgent()

    output = await agent.run(
        OpportunityAgentInput(
            vehicle_score={"score": 85, "strengths": ["Precio competitivo"]},
            profit_analysis={
                "net_profit": -500.0,
                "roi_percentage": -5.0,
                "purchase_price": 12000.0,
                "risk_level": "HIGH",
            },
            market_estimation={
                "market_price": 11000.0,
                "confidence": 40.0,
                "supply_level": 80.0,
                "demand_level": 30.0,
                "market_trend": "falling",
            },
        )
    )

    # Beneficio negativo => REJECT según las reglas reales del finder.
    assert output.recommendation == "REJECT"
    assert 0 <= output.overall_score <= 100
    assert output.opportunity_level in ("EXCELLENT", "GOOD", "AVERAGE", "POOR", "REJECT")
    assert output.estimated_profit == -500.0
    assert output.risk_level == "HIGH"


@pytest.mark.asyncio
async def test_opportunity_agent_flags_buy_now_for_strong_inputs():
    agent = OpportunityAgent()

    output = await agent.run(
        OpportunityAgentInput(
            vehicle_score={"score": 90},
            profit_analysis={
                "net_profit": 3000.0,
                "roi_percentage": 25.0,
                "purchase_price": 8000.0,
                "risk_level": "LOW",
            },
            market_estimation={
                "market_price": 12000.0,
                "confidence": 85.0,
                "supply_level": 20.0,
                "demand_level": 90.0,
                "market_trend": "rising",
            },
        )
    )

    assert output.recommendation == "BUY_NOW"
    assert output.strengths


# =============================================================================
# NegotiationAgent
# =============================================================================


@pytest.mark.asyncio
async def test_negotiation_agent_builds_real_strategy_from_primitives():
    agent = NegotiationAgent()

    output = await agent.run(
        NegotiationAgentInput(
            inspection_result={
                "defects": [
                    {
                        "category": "mechanic",
                        "description": "Frenos desgastados",
                        "severity": 7,
                        "estimated_repair_cost": 400.0,
                    }
                ],
                "overall_condition": 6,
                "has_accident_history": False,
            },
            repair_estimate={"total_repair_cost": 400.0, "parts_cost": 250.0, "labor_cost": 150.0},
            market_estimation={
                "market_price": 12000.0,
                "confidence": 70.0,
                "supply_level": 60.0,
                "demand_level": 50.0,
                "market_trend": "stable",
            },
            asking_price=13000.0,
            minimum_desired_profit=1000.0,
            target_margin=15.0,
            vehicle_score_data={"score": 65},
            profit_analysis_data={
                "net_profit": 800.0,
                "roi_percentage": 8.0,
                "risk_level": "MEDIUM",
            },
        )
    )

    assert output.estimated_vehicle_value > 0
    assert output.recommended_initial_offer > 0
    # Valor estimado determinista: market_price - reparación (12000 - 400).
    assert output.estimated_vehicle_value == pytest.approx(11600.0)
    # Price gap determinista: asking_price - valor estimado.
    assert output.price_gap == pytest.approx(1400.0)
    assert output.recommendation in ("BUY", "NEGOTIATE", "WALK_AWAY")
    assert output.negotiation_arguments
    assert output.negotiation_arguments[0].economic_impact >= (
        output.negotiation_arguments[-1].economic_impact
    )
    assert any("Frenos desgastados" in a.argument for a in output.negotiation_arguments)


@pytest.mark.asyncio
async def test_negotiation_agent_defaults_are_valid():
    agent = NegotiationAgent()

    output = await agent.run(NegotiationAgentInput())

    assert output.recommendation in ("BUY", "NEGOTIATE", "WALK_AWAY")


# =============================================================================
# AlertAgent
# =============================================================================


@pytest.mark.asyncio
async def test_alert_agent_triggers_on_rules():
    agent = AlertAgent()

    output = await agent.run(
        AlertAgentInput(
            opportunity=AlertOpportunityInput(
                opportunity_level="EXCELLENT",
                recommendation="BUY_NOW",
                estimated_profit=1200.0,
                roi=18.0,
            ),
            rules=AlertRulesInput(min_level="GOOD", min_profit=1000.0, min_roi=15.0),
        )
    )

    assert output.triggered is True
    # min_level GOOD (EXCELLENT ≥ GOOD) + min_profit + min_roi + recomendación BUY_NOW.
    assert len(output.alerts) == 4


@pytest.mark.asyncio
async def test_alert_agent_silent_when_thresholds_not_met():
    agent = AlertAgent()

    output = await agent.run(
        AlertAgentInput(
            opportunity=AlertOpportunityInput(
                opportunity_level="AVERAGE",
                recommendation="WATCH",
                estimated_profit=200.0,
            ),
            rules=AlertRulesInput(min_profit=500.0),
        )
    )

    assert output.triggered is False
    assert output.alerts == []


@pytest.mark.asyncio
async def test_alert_agent_action_recommendation_always_reported():
    agent = AlertAgent()

    output = await agent.run(
        AlertAgentInput(opportunity=AlertOpportunityInput(recommendation="NEGOTIATE"))
    )

    assert output.triggered is True
    assert any("NEGOTIATE" in a for a in output.alerts)


# =============================================================================
# BudgetSearchAgent — filtro de beneficio real
# =============================================================================


# =============================================================================
# BudgetSearchAgent — filtro de beneficio real
# =============================================================================


class _Profit:
    def __init__(self, net_profit: float) -> None:
        self.net_profit = net_profit


def _search_result(net_profit: float | None) -> SearchResult:
    """SearchResult real; solo profit_analysis importa para el filtro."""
    return SearchResult(
        vehicle={"external_id": "x"},
        vehicle_score={"score": 50},
        market_estimation={"confidence": 60},
        profit_analysis=None if net_profit is None else _Profit(net_profit),
        opportunity={"recommendation": "WATCH"},
    )


class _FakeEngine:
    def __init__(self, results: list[SearchResult]) -> None:
        self._results = results
        self.requests: list = []

    async def search(self, request):
        self.requests.append(request)
        return SearchEngineResult(
            summary=SearchSummary(total_results=len(self._results)),
            results=self._results,
            provider_issues=[],
        )


@pytest.mark.asyncio
async def test_budget_agent_filters_results_below_min_profit():
    engine = _FakeEngine([_search_result(2000.0), _search_result(100.0), _search_result(None)])
    agent = BudgetSearchAgent(search_engine=engine)

    output = await agent.run({"total_budget": 20000, "profit_margin_min": 500})

    assert output.status == "ok"
    assert len(output.results) == 2  # 2000 pasa; None no evaluable se conserva
    assert output.filtered_out_count == 1


@pytest.mark.asyncio
async def test_budget_agent_without_filter_keeps_everything():
    engine = _FakeEngine([_search_result(10.0), _search_result(5.0)])
    agent = BudgetSearchAgent(search_engine=engine)

    output = await agent.run({"total_budget": 20000, "profit_margin_min": 0})

    assert output.filtered_out_count == 0
    assert len(output.results) == 2


@pytest.mark.asyncio
async def test_budget_agent_budget_too_low_skips_engine():
    engine = _FakeEngine([])
    agent = BudgetSearchAgent(search_engine=engine)

    output = await agent.run({"total_budget": 10})

    assert output.status == "budget_too_low"
    assert output.max_purchase_price == 0.0
    assert engine.requests == []
