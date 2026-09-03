"""Tests de regresión del ciclo completo de pipeline.

Comprueba que los módulos del ciclo (agents + services de integración) se
pueden instanciar y exponen la API que espera el resto del sistema. Es un
smoke de cableado: detecta imports rotos o firmas cambiadas.
"""

from unittest.mock import MagicMock

import pytest

from app.agents.alert_agent import AlertAgent
from app.agents.opportunity_agent import OpportunityAgent
from app.agents.scoring_agent import ScoringAgent
from app.agents.search_agent import SearchAgent
from app.services.dashboard_service import DashboardService
from app.services.deal_pipeline_integration_service import (
    DealPipelineIntegrationService,
)
from app.services.opportunity_integration_service import (
    OpportunityIntegrationService,
)


def test_agents_are_instantiable_and_expose_entrypoints():
    """Los agents del ciclo se construyen y mantienen su método público unificado."""
    assert callable(SearchAgent().run)
    assert callable(OpportunityAgent().run)
    assert callable(ScoringAgent().run)
    assert callable(AlertAgent().run)


def test_scoring_agent_absorbed_rescoring():
    """El re-scoring (antiguo ReScoringAgent) vive en ScoringAgent.rescore."""
    assert callable(ScoringAgent().rescore)


@pytest.mark.asyncio
async def test_scoring_agent_delegates_to_real_scorer():
    """El ScoringAgent devuelve un score real (no un stub 0.0)."""
    agent = ScoringAgent()
    output = await agent.run(
        {"vehicle": {"price": 10000, "mileage": 50000, "year": 2019, "fuel_type": "diesel"}}
    )
    assert 0 < output.score <= 100


@pytest.mark.asyncio
async def test_alert_agent_returns_alerts_when_rules_met():
    agent = AlertAgent()

    no_alerts = await agent.run(
        {
            "opportunity": {
                "opportunity_level": "AVERAGE",
                "recommendation": "WATCH",
                "estimated_profit": 200,
            },
            "rules": {"min_profit": 500},
        }
    )
    assert no_alerts.triggered is False
    assert no_alerts.alerts == []

    alerts = await agent.run(
        {
            "opportunity": {
                "opportunity_level": "EXCELLENT",
                "recommendation": "BUY_NOW",
                "estimated_profit": 1200,
                "roi": 18.0,
            },
            "rules": {"min_level": "GOOD", "min_profit": 1000, "min_roi": 15.0},
        }
    )
    assert alerts.triggered is True
    assert any("EXCELLENT" in a for a in alerts.alerts)
    assert any("BUY_NOW" in a for a in alerts.alerts)


def test_integration_services_are_wired():
    """Los services de integración se construyen y exponen su entrypoint.

    TASK 3 (AUD-011): OpportunityIntegrationService ya no es una fachada de
    "modo análisis" sin dependencias — opera sobre una Opportunity real
    persistida, así que exige un repository y un deal_service reales
    (mockeados aquí; el comportamiento real se cubre en
    test_opportunity_integration_service.py).
    """
    opportunity_integration = OpportunityIntegrationService(
        opportunity_repository=MagicMock(),
        deal_service=MagicMock(),
    )
    deal_integration = DealPipelineIntegrationService()

    assert deal_integration.negotiation_engine is not None
    assert callable(opportunity_integration.convert_to_deal)
    assert callable(deal_integration.process_deal_pipeline)


@pytest.mark.asyncio
async def test_dashboard_summary_reports_pipeline_ready():
    result = await DashboardService().get_summary()

    assert result["pipeline_ready"] is True
    assert result["modules_connected"] == 4
    assert result["status"] == "operational"
