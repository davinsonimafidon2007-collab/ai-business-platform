"""Tests de integración para Dashboard + Opportunity Integration."""
import pytest
from app.services.dashboard_service import DashboardService
from app.services.opportunity_integration_service import OpportunityIntegrationService


@pytest.mark.asyncio
async def test_dashboard_summary():
    d = DashboardService()
    result = await d.get_summary()
    assert result["status"] == "operational"


@pytest.mark.asyncio
async def test_opportunity_integration():
    o = OpportunityIntegrationService()
    result = await o.analyze_and_create_deal(
        {"id": "test_123", "price": 10000}, "user_1"
    )
    assert "analysis" in result
