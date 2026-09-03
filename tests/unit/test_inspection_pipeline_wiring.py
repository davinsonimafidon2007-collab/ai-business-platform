"""TASK 4/6 (AUD-012): la inspección real llega a la negociación automática.

Antes de este bloque, `SearchResultAnalyzer._load_inspection_result` llamaba a
tres métodos que NO existían en `InspectionService`
(`get_latest_session_for_vehicle`, `get_session_observations`,
`build_inspection_result`), y su `except Exception` convertía el
`AttributeError` en un silencioso "no hay inspección". Además, nadie inyectaba
nunca el servicio: el analyzer lo recibía siempre como `None`.

Estos tests cubren las dos mitades del arreglo:
1. `InspectionService` expone e implementa realmente esos tres métodos.
2. El analyzer, con el servicio inyectado, usa los defectos reales en la
   negociación (y no la heurística vacía).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config.inspection import (
    InspectionItemStatus,
    InspectionSessionStatus,
    SeverityLevel,
)
from app.models.base import Base
from app.models.inspection import InspectionObservation, InspectionSession
from app.models.market import MarketEstimation
from app.models.opportunity_phase import OpportunityPhase  # noqa: F401  (mapper registry)
from app.models.vehicle import Vehicle
from app.models.vehicle_evaluation import VehicleEvaluation  # noqa: F401  (mapper registry)
from app.repositories.inspection_repository import (
    InspectionObservationRepository,
    InspectionPhotoRepository,
    InspectionSessionRepository,
)
from app.services.inspection_service import InspectionService
from app.services.opportunity_finder import OpportunityFinder
from app.services.profit_analyzer import ProfitAnalyzer
from app.services.search_result_analyzer import SearchResultAnalyzer
from app.services.vehicle_scorer import VehicleScorer

USER_ID = "00000000-0000-0000-0000-000000000099"


@dataclass
class _MarketStub:
    async def estimate_async(self, vehicle: object) -> MarketEstimation:
        return MarketEstimation(
            market_price=24000.0,
            confidence=70.0,
            supply_level=50.0,
            demand_level=60.0,
            market_trend="stable",
            comparable_count=8,
        )


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


async def _seed_vehicle_with_inspection(
    session: Any,
    *,
    status: str = InspectionItemStatus.BAD.value,
    severity: str = SeverityLevel.HIGH.value,
    repair_cost: float = 1200.0,
    session_status: str = InspectionSessionStatus.COMPLETED.value,
) -> tuple[Vehicle, InspectionSession]:
    vehicle = Vehicle(
        user_id=USER_ID,
        source="test_provider",
        external_id="ext-1",
        brand="BMW",
        model="320d",
        year=2020,
        mileage=60000,
        price=18000.0,
        currency="EUR",
    )
    session.add(vehicle)
    await session.commit()
    await session.refresh(vehicle)

    inspection = InspectionSession(
        vehicle_id=vehicle.id,
        user_id=USER_ID,
        status=session_status,
        current_category_order=1,
    )
    session.add(inspection)
    await session.commit()
    await session.refresh(inspection)

    observation = InspectionObservation(
        session_id=inspection.id,
        category_id="exterior",
        item_id="pintura",
        status=status,
        severity=severity,
        estimated_repair_cost=repair_cost,
        notes="Golpe en aleta delantera",
    )
    session.add(observation)
    await session.commit()

    return vehicle, inspection


def _make_inspection_service(session: Any) -> InspectionService:
    return InspectionService(
        session_repo=InspectionSessionRepository(session),
        observation_repo=InspectionObservationRepository(session),
        photo_repo=InspectionPhotoRepository(session),
    )


class TestInspectionServiceIntegrationMethods:
    """Los tres métodos que el analyzer necesitaba y no existían."""

    @pytest.mark.asyncio
    async def test_get_latest_session_for_vehicle(self, db_session) -> None:
        vehicle, inspection = await _seed_vehicle_with_inspection(db_session)
        service = _make_inspection_service(db_session)

        found = await service.get_latest_session_for_vehicle(vehicle.id)
        assert found is not None
        assert found.id == inspection.id

    @pytest.mark.asyncio
    async def test_get_latest_session_returns_none_without_vehicle(
        self, db_session
    ) -> None:
        service = _make_inspection_service(db_session)
        assert await service.get_latest_session_for_vehicle(None) is None
        assert (
            await service.get_latest_session_for_vehicle(
                "00000000-0000-0000-0000-0000000000ff"
            )
            is None
        )

    @pytest.mark.asyncio
    async def test_get_latest_session_prefers_completed(self, db_session) -> None:
        """Una inspección terminada gana a un borrador posterior."""
        vehicle, completed = await _seed_vehicle_with_inspection(db_session)
        draft = InspectionSession(
            vehicle_id=vehicle.id,
            user_id=USER_ID,
            status=InspectionSessionStatus.DRAFT.value,
            current_category_order=1,
        )
        db_session.add(draft)
        await db_session.commit()

        service = _make_inspection_service(db_session)
        found = await service.get_latest_session_for_vehicle(vehicle.id)
        assert found is not None
        assert found.id == completed.id

    @pytest.mark.asyncio
    async def test_get_session_observations(self, db_session) -> None:
        _, inspection = await _seed_vehicle_with_inspection(db_session)
        service = _make_inspection_service(db_session)

        observations = await service.get_session_observations(inspection.id)
        assert len(observations) == 1
        assert observations[0].item_id == "pintura"

    @pytest.mark.asyncio
    async def test_build_inspection_result_maps_defects_and_condition(
        self, db_session
    ) -> None:
        _, inspection = await _seed_vehicle_with_inspection(db_session)
        service = _make_inspection_service(db_session)
        observations = await service.get_session_observations(inspection.id)

        result = service.build_inspection_result(observations)
        assert len(result.defects) == 1
        assert result.defects[0].estimated_repair_cost == 1200.0
        # 1 observación BAD -> penalización de 2 puntos sobre 10.
        assert result.overall_condition == 8
        assert "Golpe en aleta delantera" in result.inspection_notes

    @pytest.mark.asyncio
    async def test_build_inspection_result_without_defects_is_pristine(
        self, db_session
    ) -> None:
        _, inspection = await _seed_vehicle_with_inspection(
            db_session,
            status=InspectionItemStatus.GOOD.value,
            severity=SeverityLevel.LOW.value,
            repair_cost=0.0,
        )
        service = _make_inspection_service(db_session)
        observations = await service.get_session_observations(inspection.id)

        result = service.build_inspection_result(observations)
        assert result.defects == []
        assert result.overall_condition == 10


class TestAnalyzerUsesRealInspection:
    """El pipeline de búsqueda usa la inspección real cuando está inyectada."""

    @staticmethod
    def _make_analyzer(inspection_service: Any) -> SearchResultAnalyzer:
        return SearchResultAnalyzer(
            vehicle_scorer=VehicleScorer(),
            market_estimator=_MarketStub(),
            profit_analyzer=ProfitAnalyzer(),
            opportunity_finder=OpportunityFinder(),
            import_cost_profile="SPAIN",
            inspection_service=inspection_service,
        )

    @pytest.mark.asyncio
    async def test_real_defects_reach_negotiation(self, db_session) -> None:
        vehicle, _ = await _seed_vehicle_with_inspection(db_session)
        service = _make_inspection_service(db_session)

        loaded = await self._make_analyzer(service)._load_inspection_result(vehicle)
        assert loaded is not None, "la inspección real debe llegar al analyzer"
        assert len(loaded.defects) == 1
        assert loaded.defects[0].estimated_repair_cost == 1200.0

    @pytest.mark.asyncio
    async def test_without_service_falls_back_to_none(self, db_session) -> None:
        vehicle, _ = await _seed_vehicle_with_inspection(db_session)
        loaded = await self._make_analyzer(None)._load_inspection_result(vehicle)
        assert loaded is None

    @pytest.mark.asyncio
    async def test_full_analyze_uses_real_inspection_in_negotiation(
        self, db_session
    ) -> None:
        """Con inspección real, la negociación gana apalancamiento y argumentos.

        Comparado con el mismo vehículo sin servicio de inspección inyectado
        (el comportamiento anterior a este bloque), los 1.200 € de daños
        reales aumentan el leverage del comprador y añaden un argumento de
        negociación basado en el defecto detectado.
        """
        vehicle, _ = await _seed_vehicle_with_inspection(db_session)
        service = _make_inspection_service(db_session)

        with_inspection = await self._make_analyzer(service).analyze(vehicle)
        without_inspection = await self._make_analyzer(None).analyze(vehicle)

        assert with_inspection.negotiation is not None
        assert without_inspection.negotiation is not None
        assert (
            with_inspection.negotiation.leverage_score
            > without_inspection.negotiation.leverage_score
        )
        assert len(with_inspection.negotiation.negotiation_arguments) > len(
            without_inspection.negotiation.negotiation_arguments
        )
