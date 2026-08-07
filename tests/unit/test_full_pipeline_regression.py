"""Tests de regresión del ciclo completo de pipeline."""
import pytest
from app.services.dashboard_service import DashboardService
from app.services.opportunity_integration_service import OpportunityIntegrationService
from app.services.deal_pipeline_integration_service import DealPipelineIntegrationService
from app.agents.search_agent import SearchAgent
from app.agents.opportunity_agent import OpportunityAgent
from app.agents.scoring_agent import ScoringAgent


@pytest.mark.asyncio
async def test_full_pipeline_integrated():
    """Verifica que todos los módulos del ciclo estén conectados."""
    agent_search = SearchAgent("test")
    agent_opportunity = OpportunityAgent()
    agent_scoring = ScoringAgent()

    dashboard = DashboardService()
    opportunity_int = OpportunityIntegrationService()
    deal_int = DealPipelineIntegrationService()

    # Verificar que los módulos no fallen al instanciar
    result = await dashboard.get_summary()
    assert result["pipeline_ready"] is True
    assert result["modules_connected"] == 4
