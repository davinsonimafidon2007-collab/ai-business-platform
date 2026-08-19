from unittest.mock import AsyncMock

import pytest

from app.models.search_order import SearchOrder
from app.schemas.vehicle import VehicleCreate
from app.services.opportunity_finder import OpportunityFinder
from app.services.pipeline_orchestrator import PipelineOrchestrator
from app.services.profit_analyzer import ProfitAnalyzer
from app.services.search_engine_service import SearchEngineService


@pytest.mark.integration_db
class TestPipelineOrchestrator:
    """Tests de integración para el PipelineOrchestrator."""

    @pytest.fixture
    def mock_search_engine(self):
        """Mock del SearchEngineService."""
        engine = AsyncMock(spec=SearchEngineService)
        engine.search.return_value = [
            VehicleCreate(
                brand="BMW",
                model="Series 3",
                year=2020,
                price=25000,
                mileage=50000,
                fuel_type="gasoline",
                external_id="test-123",
                provider="autoscout24",
            )
        ]
        return engine

    @pytest.fixture
    def mock_opportunity_finder(self):
        """Mock del OpportunityFinder."""
        finder = AsyncMock(spec=OpportunityFinder)
        finder.find_opportunities.return_value = [
            {
                "vehicle_id": "test-123",
                "recommendation": "BUY",
                "score": 85,
                "estimated_profit": 3500,
            }
        ]
        return finder

    @pytest.fixture
    def mock_profit_analyzer(self):
        """Mock del ProfitAnalyzer."""
        analyzer = AsyncMock(spec=ProfitAnalyzer)
        analyzer.analyze.return_value = {
            "total_cost": 28000,
            "market_value": 31500,
            "net_profit": 3500,
            "margin_percent": 12.5,
        }
        return analyzer

    @pytest.fixture
    def pipeline_orchestrator(
        self, mock_search_engine, mock_opportunity_finder, mock_profit_analyzer
    ):
        """Instancia del PipelineOrchestrator con mocks."""
        return PipelineOrchestrator(
            search_engine=mock_search_engine,
            opportunity_finder=mock_opportunity_finder,
            profit_analyzer=mock_profit_analyzer,
        )

    @pytest.mark.asyncio
    async def test_pipeline_executes_end_to_end(self, pipeline_orchestrator, db_session):
        """Test que el pipeline completo se ejecuta sin errores."""
        search_order = SearchOrder(
            user_id=1,
            brand="BMW",
            model="Series 3",
            min_price=20000,
            max_price=30000,
            status="PENDING",
        )
        db_session.add(search_order)
        await db_session.commit()
        await db_session.refresh(search_order)

        # Ejecutar pipeline
        result = await pipeline_orchestrator.run_pipeline(search_order)

        # Verificar que hay resultados
        assert result is not None
        assert len(result.vehicles) > 0
        assert len(result.opportunities) > 0

    @pytest.mark.asyncio
    async def test_pipeline_handles_provider_failure_gracefully(
        self, pipeline_orchestrator, mock_search_engine, db_session
    ):
        """Test que el pipeline maneja fallos de proveedores sin crash."""
        # Simular fallo de proveedor
        mock_search_engine.search.side_effect = Exception("Provider timeout")

        search_order = SearchOrder(
            user_id=1,
            brand="Audi",
            model="A4",
            status="PENDING",
        )
        db_session.add(search_order)
        await db_session.commit()
        await db_session.refresh(search_order)

        # Ejecutar pipeline - no debe lanzar excepción
        result = await pipeline_orchestrator.run_pipeline(search_order)

        # Debe devolver resultado vacío pero sin crash
        assert result is not None
        assert len(result.vehicles) == 0
        assert len(result.provider_issues) > 0

    @pytest.mark.asyncio
    async def test_pipeline_exposes_provider_issues(
        self, pipeline_orchestrator, mock_search_engine, db_session
    ):
        """Test que el pipeline expone problemas de proveedores correctamente."""
        from app.schemas.search import ProviderIssue

        # Simular problema de proveedor
        mock_search_engine.search.return_value = []
        mock_search_engine.last_provider_issues = [
            ProviderIssue(
                provider="autoscout24",
                stage="search",
                error_type="timeout",
                message="Request timeout after 30s",
            )
        ]

        search_order = SearchOrder(
            user_id=1,
            brand="Mercedes",
            model="C-Class",
            status="PENDING",
        )
        db_session.add(search_order)
        await db_session.commit()
        await db_session.refresh(search_order)

        result = await pipeline_orchestrator.run_pipeline(search_order)

        # Verificar que los problemas de proveedor están expuestos
        assert len(result.provider_issues) > 0
        assert result.provider_issues[0].provider == "autoscout24"
        assert result.provider_issues[0].error_type == "timeout"

    @pytest.mark.asyncio
    async def test_pipeline_updates_search_order_status(self, pipeline_orchestrator, db_session):
        """Test que el pipeline actualiza el estado de la orden de búsqueda."""
        search_order = SearchOrder(
            user_id=1,
            brand="Volkswagen",
            model="Golf",
            status="PENDING",
        )
        db_session.add(search_order)
        await db_session.commit()
        await db_session.refresh(search_order)

        await pipeline_orchestrator.run_pipeline(search_order)
        await db_session.refresh(search_order)

        # El estado debe haber cambiado de PENDING
        assert search_order.status in ["COMPLETED", "FAILED", "RUNNING"]
