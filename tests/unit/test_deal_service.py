"""Tests del servicio de deals: máquina de estados, idempotencia,
concurrencia y auditoría."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from app.exceptions.base import AppError
from app.models.deal import Deal, DealStatus
from app.services.deal_service import DealService

ALL_STATUSES = list(DealStatus)


def _make_deal(
    *,
    deal_id: str = "deal-1",
    user_id: str = "user-1",
    status: DealStatus = DealStatus.NEW,
) -> Deal:
    return Deal(
        id=deal_id,
        user_id=user_id,
        status=status,
        opportunity_id=None,
        vehicle_id=None,
    )


def _make_service(
    deal: Deal | None = None,
    active_for_opportunity: Deal | None = None,
) -> tuple[DealService, AsyncMock]:
    repo = AsyncMock()
    repo.get_by_id.return_value = deal
    repo.update.return_value = deal
    repo.save_transition.return_value = deal
    repo.get_active_by_opportunity.return_value = active_for_opportunity
    return DealService(repo), repo


# ---------------------------------------------------------------------------
# Máquina de estados: matriz de transiciones
# ---------------------------------------------------------------------------

VALID_TRANSITIONS = {
    DealStatus.NEW: {
        DealStatus.ANALYZING,
        DealStatus.CANCELLED,
    },
    DealStatus.ANALYZING: {
        DealStatus.NEGOTIATING,
        DealStatus.LOST,
        DealStatus.CANCELLED,
    },
    DealStatus.NEGOTIATING: {
        DealStatus.WON,
        DealStatus.LOST,
        DealStatus.CANCELLED,
    },
    # TASK 3 (cumplimiento físico, fusionado con origin/main v2): WON ya NO
    # es terminal, continúa hasta SOLD.
    DealStatus.WON: {
        DealStatus.BOUGHT,
        DealStatus.CANCELLED,
    },
    DealStatus.BOUGHT: {
        DealStatus.IN_TRANSIT,
        DealStatus.CANCELLED,
    },
    DealStatus.IN_TRANSIT: {
        DealStatus.REGISTERED,
        DealStatus.CANCELLED,
    },
    DealStatus.REGISTERED: {
        DealStatus.SOLD,
        DealStatus.CANCELLED,
    },
}


class TestTransitionMatrix:
    @pytest.mark.asyncio
    async def test_all_valid_transitions_succeed(self) -> None:
        """Cada transición válida de la máquina se aplica correctamente."""
        for current, targets in VALID_TRANSITIONS.items():
            for target in targets:
                deal = _make_deal(status=current)
                service, _ = _make_service(deal)
                before = deal.updated_at
                extra_kwargs = {"sale_price": 15000.0} if target == DealStatus.SOLD else {}
                result = await service.transition(
                    deal_id="deal-1", user_id="user-1", new_status=target, **extra_kwargs
                )
                assert result.status == target, f"{current} -> {target}"
                assert result.status_changed_at >= before
                if target.is_terminal:
                    assert result.closed_at is not None
                else:
                    assert result.closed_at is None

    @pytest.mark.asyncio
    async def test_all_invalid_transitions_rejected(self) -> None:
        """Toda transición fuera del mapa -> 422 (incluye saltos y retrocesos)."""
        for current in ALL_STATUSES:
            allowed = VALID_TRANSITIONS.get(current, set())
            for target in ALL_STATUSES:
                if target == current or target in allowed:
                    continue
                deal = _make_deal(status=current)
                service, _ = _make_service(deal)
                with pytest.raises((HTTPException, AppError)) as exc:
                    await service.transition(
                        deal_id="deal-1", user_id="user-1", new_status=target
                    )
                assert exc.value.status_code == 422, f"{current} -X {target}"

    @pytest.mark.asyncio
    async def test_terminal_states_have_no_exits(self) -> None:
        """SOLD/LOST/CANCELLED no transicionan a nada (422).

        WON ya NO es terminal desde TASK 3 (fusionado con origin/main v2):
        continúa hasta BOUGHT -> IN_TRANSIT -> REGISTERED -> SOLD.
        """
        for terminal in (
            DealStatus.SOLD,
            DealStatus.LOST,
            DealStatus.CANCELLED,
        ):
            assert DealService.allowed_transitions(terminal) == set()


# ---------------------------------------------------------------------------
# Idempotencia
# ---------------------------------------------------------------------------


class TestIdempotency:
    @pytest.mark.asyncio
    async def test_same_state_is_noop_success(self) -> None:
        """Transicionar al estado actual devuelve el deal sin escribir."""
        for state in ALL_STATUSES:
            deal = _make_deal(status=state)
            service, repo = _make_service(deal)
            result = await service.transition(
                deal_id="deal-1", user_id="user-1", new_status=state
            )
            assert result.status == state
            # No debe haber ninguna escritura.
            repo.save_transition.assert_not_called()
            repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_repeat_terminal_transition_stays_idempotent(self) -> None:
        """Repetir WON sobre un deal WON -> 200 sin cambios."""
        deal = _make_deal(status=DealStatus.WON)
        service, repo = _make_service(deal)
        result = await service.transition(
            deal_id="deal-1", user_id="user-1", new_status=DealStatus.WON
        )
        assert result.status == DealStatus.WON
        repo.save_transition.assert_not_called()

    @pytest.mark.asyncio
    async def test_new_to_won_jump_rejected(self) -> None:
        """NEW -> WON directo es imposible (422): hay que pasar por el flujo."""
        deal = _make_deal(status=DealStatus.NEW)
        service, _ = _make_service(deal)
        with pytest.raises((HTTPException, AppError)) as exc:
            await service.transition(
                deal_id="deal-1", user_id="user-1", new_status=DealStatus.WON
            )
        assert exc.value.status_code == 422


# ---------------------------------------------------------------------------
# Concurrencia
# ---------------------------------------------------------------------------


class TestConcurrency:
    @pytest.mark.asyncio
    async def test_transition_reads_with_row_lock(self) -> None:
        """La lectura para transicionar pide FOR UPDATE."""
        deal = _make_deal(status=DealStatus.NEW)
        service, repo = _make_service(deal)
        await service.transition(
            deal_id="deal-1",
            user_id="user-1",
            new_status=DealStatus.ANALYZING,
        )
        repo.get_by_id.assert_called_once_with("deal-1", for_update=True)

    @pytest.mark.asyncio
    async def test_optimistic_lock_conflict_returns_409(self) -> None:
        """Escritura perdida (StaleDataError) -> 409 Conflict."""
        deal = _make_deal(status=DealStatus.NEW)
        service, repo = _make_service(deal)
        repo.save_transition.side_effect = StaleDataError("stmt", {}, None)
        with pytest.raises((HTTPException, AppError)) as exc:
            await service.transition(
                deal_id="deal-1",
                user_id="user-1",
                new_status=DealStatus.ANALYZING,
            )
        assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# Auditoría e historial
# ---------------------------------------------------------------------------


class TestAuditTrail:
    @pytest.mark.asyncio
    async def test_transition_persists_history_and_audit_atomically(self) -> None:
        """Cada transición persiste DealStatusHistory + AuditLog en la misma tx."""
        deal = _make_deal(status=DealStatus.ANALYZING)
        deal.offer_price = None
        service, repo = _make_service(deal)
        await service.transition(
            deal_id="deal-1",
            user_id="user-1",
            new_status=DealStatus.NEGOTIATING,
            notes="contraoferta",
            offer_price=15000.0,
        )
        repo.save_transition.assert_awaited_once()
        saved_deal, history, audit = repo.save_transition.await_args.args
        assert saved_deal.id == "deal-1"
        assert history.from_status == "ANALYZING"
        assert history.to_status == "NEGOTIATING"
        assert history.changed_by_user_id == "user-1"
        assert history.notes == "contraoferta"
        assert float(history.offer_price) == 15000.0
        assert audit.action == "deal_status_changed"
        assert audit.resource == "deal"
        assert audit.resource_id == "deal-1"
        assert "ANALYZING" in audit.details and "NEGOTIATING" in audit.details

    @pytest.mark.asyncio
    async def test_create_persists_creation_history(self) -> None:
        """La creación registra la fila inicial (NULL -> NEW) en historial."""
        service, repo = _make_service(_make_deal())
        await service.create(user_id="user-1", opportunity_id="opp-1")
        _, history, audit = repo.save_transition.await_args.args
        assert history.from_status is None
        assert history.to_status == "NEW"
        assert audit.action == "deal_created"

    @pytest.mark.asyncio
    async def test_get_history_requires_ownership(self) -> None:
        """Historial de un deal ajeno -> 404."""
        deal = _make_deal(user_id="user-2")
        service, repo = _make_service(deal)
        repo.list_history.return_value = ([], 0)
        with pytest.raises((HTTPException, AppError)) as exc:
            await service.get_history("deal-1", "user-1")
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_writes_audit_entry(self) -> None:
        """El borrado persiste una entrada de auditoría en la misma tx."""
        deal = _make_deal()
        service, repo = _make_service(deal)
        await service.delete("deal-1", "user-1")
        deleted_deal, audit = repo.delete.await_args.args
        assert deleted_deal.id == "deal-1"
        assert audit.action == "deal_deleted"


# ---------------------------------------------------------------------------
# Creación: validaciones y duplicados
# ---------------------------------------------------------------------------


class TestCreate:
    @pytest.mark.asyncio
    async def test_create_requires_opportunity_or_vehicle(self) -> None:
        """Sin opportunity_id ni vehicle_id -> 422."""
        service, _ = _make_service(_make_deal())
        with pytest.raises((HTTPException, AppError)) as exc:
            await service.create(user_id="user-1")
        assert exc.value.status_code == 422

    @pytest.mark.asyncio
    async def test_create_ok_with_opportunity(self) -> None:
        """Con opportunity_id -> crea deal en estado NEW."""
        service, _ = _make_service(_make_deal())
        result = await service.create(user_id="user-1", opportunity_id="opp-1")
        assert result.status == DealStatus.NEW

    @pytest.mark.asyncio
    async def test_create_ok_with_vehicle(self) -> None:
        """Con vehicle_id -> crea deal en estado NEW."""
        service, _ = _make_service(_make_deal())
        result = await service.create(user_id="user-1", vehicle_id="vehicle-1")
        assert result.status == DealStatus.NEW

    @pytest.mark.asyncio
    async def test_create_duplicate_active_opportunity_conflict(self) -> None:
        """Segundo create con misma opportunity activa -> 409."""
        existing = _make_deal(deal_id="deal-existing", status=DealStatus.NEGOTIATING)
        service, _ = _make_service(_make_deal(), active_for_opportunity=existing)
        with pytest.raises((HTTPException, AppError)) as exc:
            await service.create(user_id="user-1", opportunity_id="opp-1")
        assert exc.value.status_code == 409
        deal_id = getattr(exc.value, "deal_id", None)
        if deal_id is None:
            details = getattr(exc.value, "details", None)
            if isinstance(details, dict):
                deal_id = details.get("deal_id")
        if deal_id is None and hasattr(exc.value, "detail"):
            try:
                detail = exc.value.detail  # type: ignore[union-attr]
                if isinstance(detail, dict):
                    deal_id = detail.get("deal_id")
            except Exception:
                deal_id = None
        assert deal_id == "deal-existing"

    @pytest.mark.asyncio
    async def test_create_race_lost_by_unique_index_returns_409(self) -> None:
        """Carrera en creación: IntegrityError del índice único -> 409."""
        service, repo = _make_service(_make_deal(), active_for_opportunity=None)
        repo.save_transition.side_effect = IntegrityError(
            "INSERT", {}, Exception("uq_deals_active_per_opportunity")
        )
        with pytest.raises((HTTPException, AppError)) as exc:
            await service.create(user_id="user-1", opportunity_id="opp-1")
        assert exc.value.status_code == 409

    @pytest.mark.asyncio
    async def test_create_after_terminal_allowed(self) -> None:
        """Tras WON/LOST/CANCELLED, nuevo create -> permitido (nuevo ciclo)."""
        service, _ = _make_service(_make_deal(), active_for_opportunity=None)
        result = await service.create(user_id="user-1", opportunity_id="opp-1")
        assert result.status == DealStatus.NEW


# ---------------------------------------------------------------------------
# Validación de datos
# ---------------------------------------------------------------------------


class TestDataValidation:
    @pytest.mark.asyncio
    async def test_negative_offer_price_rejected(self) -> None:
        """offer_price negativo -> 422, sin tocar el deal."""
        deal = _make_deal(status=DealStatus.ANALYZING)
        service, repo = _make_service(deal)
        with pytest.raises((HTTPException, AppError)) as exc:
            await service.transition(
                deal_id="deal-1",
                user_id="user-1",
                new_status=DealStatus.NEGOTIATING,
                offer_price=-1.0,
            )
        assert exc.value.status_code == 422
        repo.get_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_zero_offer_price_allowed(self) -> None:
        """offer_price 0 no es negativo: pasa la validación de datos."""
        deal = _make_deal(status=DealStatus.ANALYZING)
        service, _ = _make_service(deal)
        result = await service.transition(
            deal_id="deal-1",
            user_id="user-1",
            new_status=DealStatus.NEGOTIATING,
            offer_price=0.0,
        )
        assert result.status == DealStatus.NEGOTIATING


# ---------------------------------------------------------------------------
# Ownership
# ---------------------------------------------------------------------------


class TestOwnership:
    @pytest.mark.asyncio
    async def test_transition_foreign_deal_rejected(self) -> None:
        """Transición sobre deal ajeno -> 404."""
        deal = _make_deal(user_id="user-2", status=DealStatus.NEW)
        service, _ = _make_service(deal)
        with pytest.raises((HTTPException, AppError)) as exc:
            await service.transition(
                deal_id="deal-1",
                user_id="user-1",
                new_status=DealStatus.ANALYZING,
            )
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_missing_deal_rejected(self) -> None:
        """Deal inexistente -> 404."""
        service, repo = _make_service(None)
        repo.get_by_id.return_value = None
        with pytest.raises((HTTPException, AppError)) as exc:
            await service.transition(
                deal_id="missing",
                user_id="user-1",
                new_status=DealStatus.ANALYZING,
            )
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_foreign_deal_rejected(self) -> None:
        """GET de un deal ajeno -> 404 (no filtra existencia)."""
        deal = _make_deal(user_id="user-2")
        service, _ = _make_service(deal)
        with pytest.raises((HTTPException, AppError)) as exc:
            await service.get("deal-1", "user-1")
        assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# Task E.2 — Guardar última simulación en el deal
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_simulation_ok() -> None:
    """Guardar simulación en un deal propio actualiza los campos last_sim_*."""
    deal = _make_deal(status=DealStatus.NEW, user_id="user-1")
    service, _ = _make_service(deal)
    result = await service.save_simulation(
        deal_id="deal-1",
        user_id="user-1",
        purchase_price=18000.0,
        estimated_sale_price=24000.0,
        total_cost=21500.0,
        net_profit=2500.0,
        roi_percentage=11.63,
        profile_name="SPAIN",
    )
    assert result.last_sim_purchase_price == 18000.0
    assert result.last_sim_sale_price == 24000.0
    assert result.last_sim_total_cost == 21500.0
    assert result.last_sim_net_profit == 2500.0
    assert result.last_sim_roi == 11.63
    assert result.last_sim_profile == "SPAIN"
    assert result.last_sim_at is not None
    # No toca el status del pipeline ni los timestamps de estado.
    assert result.status == DealStatus.NEW


@pytest.mark.asyncio
async def test_save_simulation_does_not_change_status() -> None:
    """Guardar simulación no cambia el estado del deal."""
    deal = _make_deal(status=DealStatus.NEGOTIATING, user_id="user-1")
    service, _ = _make_service(deal)
    result = await service.save_simulation(
        deal_id="deal-1",
        user_id="user-1",
        net_profit=1000.0,
        roi_percentage=5.0,
        profile_name="ES",
    )
    assert result.status == DealStatus.NEGOTIATING
    assert result.last_sim_net_profit == 1000.0


@pytest.mark.asyncio
async def test_save_simulation_ownership_rejected() -> None:
    """Guardar simulación sobre deal ajeno -> 404."""
    deal = _make_deal(user_id="user-2", status=DealStatus.NEW)
    service, _ = _make_service(deal)
    with pytest.raises((HTTPException, AppError)) as exc:
        await service.save_simulation(
            deal_id="deal-1",
            user_id="user-1",
            net_profit=1000.0,
        )
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# Timestamps
# ---------------------------------------------------------------------------


class TestTimestamps:
    @pytest.mark.asyncio
    async def test_closed_at_set_on_terminal_cleared_on_reopen(self) -> None:
        """closed_at se rellena al llegar a terminal y se limpia si vuelve.

        WON ya NO es terminal (TASK 3): se prueba con SOLD, el terminal real
        del cumplimiento físico.
        """
        # Un deal nunca puede salir de terminal, así que solo probamos el alta.
        deal = _make_deal(status=DealStatus.REGISTERED)
        deal.closed_at = None
        service, _ = _make_service(deal)
        result = await service.transition(
            deal_id="deal-1", user_id="user-1", new_status=DealStatus.SOLD, sale_price=15000.0
        )
        assert result.closed_at is not None
        assert result.status_changed_at <= datetime.now(UTC)

    @pytest.mark.asyncio
    async def test_created_deal_has_status_changed_at(self) -> None:
        """Un deal recién creado ya tiene status_changed_at."""
        deal = _make_deal()
        assert deal.status_changed_at is not None
        assert deal.created_at is not None
