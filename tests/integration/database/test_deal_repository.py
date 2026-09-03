"""Integration tests for DealRepository and the TASK 3 fulfillment pipeline.

Verifies CRUD + the BOUGHT/IN_TRANSIT/REGISTERED/SOLD flow against a
temporary SQLite database (via DealService, which is what actually
enforces transitions and computes actual_profit).
"""

from __future__ import annotations

import pytest

from app.models.deal import Deal, DealStatus
from app.repositories.deal_repository import DealRepository
from app.repositories.vehicle_evaluation_repository import VehicleEvaluationRepository
from app.services.deal_service import DealService

USER_ID = "00000000-0000-0000-0000-000000000099"


class TestDealRepositoryCrud:
    @pytest.mark.asyncio
    async def test_create_and_get(self, deal_repo: DealRepository) -> None:
        deal = Deal(user_id=USER_ID, notes="test")
        created = await deal_repo.create(deal)
        assert created.id is not None
        fetched = await deal_repo.get_by_id(created.id)
        assert fetched is not None
        assert fetched.notes == "test"

    @pytest.mark.asyncio
    async def test_list_for_user_total_is_correct_with_multiple_rows(
        self, deal_repo: DealRepository
    ) -> None:
        """Regresión (TASK 3): el total no debe duplicarse/elevarse al
        cuadrado. func.count(Deal.id).select_from(subquery) producía un
        producto cartesiano; con 3 deals devolvía total=9 en vez de 3."""
        for i in range(3):
            await deal_repo.create(Deal(user_id=USER_ID, notes=f"deal-{i}"))

        items, total = await deal_repo.list_for_user(user_id=USER_ID)
        assert total == 3
        assert len(items) == 3

    @pytest.mark.asyncio
    async def test_list_for_user_filters_by_status(
        self, deal_repo: DealRepository
    ) -> None:
        await deal_repo.create(Deal(user_id=USER_ID, status=DealStatus.NEW))
        await deal_repo.create(Deal(user_id=USER_ID, status=DealStatus.WON))

        items, total = await deal_repo.list_for_user(
            user_id=USER_ID, status=DealStatus.WON
        )
        assert total == 1
        assert items[0].status == DealStatus.WON

    @pytest.mark.asyncio
    async def test_get_active_by_opportunity_includes_fulfillment_states(
        self, deal_repo: DealRepository
    ) -> None:
        """Un deal ya en BOUGHT sigue bloqueando un segundo deal para la
        misma oportunidad (antes de TASK 3 solo NEW|CONTACTED|OFFER)."""
        deal = Deal(
            user_id=USER_ID,
            opportunity_id="00000000-0000-0000-0000-0000000000aa",
            status=DealStatus.BOUGHT,
        )
        await deal_repo.create(deal)

        active = await deal_repo.get_active_by_opportunity(
            USER_ID, "00000000-0000-0000-0000-0000000000aa"
        )
        assert active is not None
        assert active.id == deal.id


class TestDealFulfillmentFlow:
    """Recorre WON -> BOUGHT -> IN_TRANSIT -> REGISTERED -> SOLD vía DealService
    contra una BD real, verificando persistencia y el cálculo de actual_profit."""

    @pytest.mark.asyncio
    async def test_full_fulfillment_flow_computes_real_profit(
        self,
        deal_repo: DealRepository,
        vehicle_evaluation_repo: VehicleEvaluationRepository,
    ) -> None:
        service = DealService(deal_repo, vehicle_evaluation_repo)
        deal = await service.create(
            user_id=USER_ID,
            vehicle_id="00000000-0000-0000-0000-0000000000bb",
            notes="flow",
        )
        deal = await service.transition(
            deal_id=deal.id, user_id=USER_ID, new_status=DealStatus.ANALYZING
        )
        deal = await service.transition(
            deal_id=deal.id,
            user_id=USER_ID,
            new_status=DealStatus.NEGOTIATING,
            offer_price=15000.0,
        )
        deal = await service.transition(
            deal_id=deal.id, user_id=USER_ID, new_status=DealStatus.WON
        )
        assert deal.status == DealStatus.WON

        deal = await service.transition(
            deal_id=deal.id,
            user_id=USER_ID,
            new_status=DealStatus.BOUGHT,
            actual_purchase_price=14800.0,
        )
        assert deal.actual_purchase_price == 14800.0
        assert deal.bought_at is not None

        deal = await service.transition(
            deal_id=deal.id,
            user_id=USER_ID,
            new_status=DealStatus.IN_TRANSIT,
            transport_carrier="Acme Transportes",
            transport_cost=900.0,
        )
        assert deal.transport_carrier == "Acme Transportes"
        assert deal.transport_started_at is not None

        deal = await service.transition(
            deal_id=deal.id,
            user_id=USER_ID,
            new_status=DealStatus.REGISTERED,
            registration_plate="1234ABC",
            registration_cost=450.0,
        )
        assert deal.registration_plate == "1234ABC"
        assert deal.registered_at is not None
        assert deal.transport_completed_at is not None

        deal = await service.transition(
            deal_id=deal.id,
            user_id=USER_ID,
            new_status=DealStatus.SOLD,
            sale_price=19000.0,
            buyer_name="Juan Pérez",
        )
        assert deal.status == DealStatus.SOLD
        assert deal.sale_price == 19000.0
        assert deal.sold_at is not None
        # 19000 - (14800 compra + 900 transporte + 450 matriculación) = 2850
        assert deal.actual_profit == pytest.approx(2850.0, abs=0.01)

        # Terminal: no admite más transiciones.
        from app.exceptions.base import DealValidationError

        with pytest.raises(DealValidationError) as exc:
            await service.transition(
                deal_id=deal.id, user_id=USER_ID, new_status=DealStatus.CANCELLED
            )
        assert exc.value.status_code == 422

    @pytest.mark.asyncio
    async def test_cancelled_reachable_after_bought(
        self,
        deal_repo: DealRepository,
        vehicle_evaluation_repo: VehicleEvaluationRepository,
    ) -> None:
        """Un trato puede cancelarse (CANCELLED) después de comprado, p.ej. si
        el transporte o la matriculación fallan — no es un estado LOST."""
        service = DealService(deal_repo, vehicle_evaluation_repo)
        deal = await service.create(
            user_id=USER_ID, vehicle_id="00000000-0000-0000-0000-0000000000bb"
        )
        deal.status = DealStatus.WON
        deal = await deal_repo.update(deal)
        deal = await service.transition(
            deal_id=deal.id, user_id=USER_ID, new_status=DealStatus.BOUGHT
        )
        deal = await service.transition(
            deal_id=deal.id, user_id=USER_ID, new_status=DealStatus.CANCELLED
        )
        assert deal.status == DealStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_sold_without_sale_price_rejected(
        self,
        deal_repo: DealRepository,
        vehicle_evaluation_repo: VehicleEvaluationRepository,
    ) -> None:
        from app.exceptions.base import DealValidationError

        service = DealService(deal_repo, vehicle_evaluation_repo)
        deal = await service.create(
            user_id=USER_ID, vehicle_id="00000000-0000-0000-0000-0000000000bb"
        )
        deal.status = DealStatus.REGISTERED
        deal = await deal_repo.update(deal)

        with pytest.raises(DealValidationError) as exc:
            await service.transition(
                deal_id=deal.id, user_id=USER_ID, new_status=DealStatus.SOLD
            )
        assert exc.value.status_code == 422
