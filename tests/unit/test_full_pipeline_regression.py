"""Tests de regresión del ciclo completo de pipeline.

Comprueba que los módulos del ciclo (agents + services de integración) se
pueden instanciar y exponen la API que espera el resto del sistema. Es un
smoke de cableado: detecta imports rotos o firmas cambiadas.
"""

import pytest

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
    """Los agents del ciclo se construyen y mantienen su método público."""
    assert callable(SearchAgent("test").run)
    assert callable(OpportunityAgent().evaluate)
    assert callable(ScoringAgent().score)


def test_integration_services_are_wired():
    """Los services de integración se construyen sin dependencias obligatorias."""
    opportunity_integration = OpportunityIntegrationService()
    deal_integration = DealPipelineIntegrationService()

    # Sin deal_service inyectado siguen siendo utilizables (modo análisis).
    assert opportunity_integration.opportunity_finder is not None
    assert deal_integration.negotiation_engine is not None
    assert callable(opportunity_integration.analyze_and_create_deal)
    assert callable(deal_integration.process_deal_pipeline)


@pytest.mark.asyncio
async def test_dashboard_summary_reports_pipeline_ready():
    result = await DashboardService().get_summary()

    assert result["pipeline_ready"] is True
    assert result["modules_connected"] == 4
    assert result["status"] == "operational"
