"""Tests de la API de deals: auth, create, list, transiciones, historial."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.database import get_db_session
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.deal import Deal, DealStatus, DealStatusHistory
from app.models.user import User
from app.repositories.deal_repository import DealRepository
from app.repositories.vehicle_repository import VehicleRepository

client = TestClient(app)


def _make_deal(
    *,
    deal_id: str = "deal-1",
    user_id: str = "user-1",
    status: DealStatus = DealStatus.NEW,
    opportunity_id: str | None = "opp-1",
    vehicle_id: str | None = "vehicle-1",
) -> Deal:
    return Deal(
        id=deal_id,
        user_id=user_id,
        opportunity_id=opportunity_id,
        vehicle_id=vehicle_id,
        status=status,
        notes=None,
        offer_price=None,
        contact_channel=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _make_history(deal_id: str) -> list[DealStatusHistory]:
    return [
        DealStatusHistory(
            deal_id=deal_id,
            from_status=None,
            to_status="NEW",
            changed_by_user_id="user-1",
            created_at=datetime.now(UTC),
        ),
        DealStatusHistory(
            deal_id=deal_id,
            from_status="NEW",
            to_status="ANALYZING",
            changed_by_user_id="user-1",
            created_at=datetime.now(UTC),
        ),
    ]


@pytest.fixture
def auth_override() -> None:
    """Override get_current_user con un usuario mock."""
    current_user = User(id="user-1", email="test@example.com", hashed_password="x")

    async def _get_current_user() -> User:
        return current_user

    app.dependency_overrides[get_current_user] = _get_current_user
    yield
    app.dependency_overrides.clear()


def test_deals_requires_auth() -> None:
    """Sin token -> 401."""
    with patch.object(settings, "auth_disabled", False):
        response = client.get("/api/v1/deals")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /deals
# ---------------------------------------------------------------------------


def test_create_deal_returns_201(auth_override: None) -> None:
    """POST /deals con auth -> 201 y status NEW."""
    deal = _make_deal()

    async def _fake_save_transition(self, deal_arg, history, audit_log=None):
        return deal

    async def _fake_get_active(self, user_id, opportunity_id):
        return None

    async def _get_db_session() -> AsyncMock:
        session = AsyncMock()
        return session

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(DealRepository, "save_transition", _fake_save_transition)
        mp.setattr(DealRepository, "get_active_by_opportunity", _fake_get_active)
        app.dependency_overrides[get_db_session] = _get_db_session

        response = client.post(
            "/api/v1/deals",
            json={"opportunity_id": "opp-1", "notes": "compra interesante"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "NEW"
        assert data["id"]  # id generado (UUID)
        assert data["closed_at"] is None
        assert data["version"] == 0


def test_create_deal_without_link_returns_422(auth_override: None) -> None:
    """POST /deals sin opportunity ni vehicle -> 422."""
    async def _get_db_session() -> AsyncMock:
        return AsyncMock()

    with pytest.MonkeyPatch.context() as mp:
        app.dependency_overrides[get_db_session] = _get_db_session
        response = client.post("/api/v1/deals", json={"notes": "sin vinculo"})
        assert response.status_code == 422


def test_create_deal_by_external_id_resolves_vehicle(auth_override: None) -> None:
    """POST /deals con source+external_id (sin vehicle_id) resuelve el
    vehículo interno y crea el deal -> 201 (no 500 por FK nula)."""
    deal = _make_deal(vehicle_id="vehicle-real-uuid")

    class _FakeVehicle:
        id = "vehicle-real-uuid"

    async def _fake_get_by_external_id(self, source, external_id, user_id=None):
        return _FakeVehicle()

    async def _fake_save_transition(self, deal_arg, history, audit_log=None):
        return deal

    async def _fake_get_active(self, user_id, opportunity_id):
        return None

    async def _get_db_session() -> AsyncMock:
        return AsyncMock()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(VehicleRepository, "get_by_external_id", _fake_get_by_external_id)
        mp.setattr(DealRepository, "save_transition", _fake_save_transition)
        mp.setattr(DealRepository, "get_active_by_opportunity", _fake_get_active)
        app.dependency_overrides[get_db_session] = _get_db_session

        response = client.post(
            "/api/v1/deals",
            json={"source": "autoscout24", "external_id": "ext-123"},
        )
        assert response.status_code == 201
        assert response.json()["vehicle_id"] == "vehicle-real-uuid"


def test_create_deal_unresolvable_external_id_returns_404_not_500(
    auth_override: None,
) -> None:
    """POST /deals con source+external_id que no resuelve a ningún vehículo
    -> 404 explícito, nunca 500 por vehicle_id=None violando la FK."""

    async def _fake_get_by_external_id(self, source, external_id, user_id=None):
        return None

    async def _get_db_session() -> AsyncMock:
        return AsyncMock()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(VehicleRepository, "get_by_external_id", _fake_get_by_external_id)
        app.dependency_overrides[get_db_session] = _get_db_session

        response = client.post(
            "/api/v1/deals",
            json={"source": "autoscout24", "external_id": "does-not-exist"},
        )
        assert response.status_code == 404


def test_create_duplicate_active_returns_409(auth_override: None) -> None:
    """POST /deals con opportunity con deal activo -> 409."""
    existing = _make_deal(
        deal_id="deal-existing", status=DealStatus.NEGOTIATING, opportunity_id="opp-1"
    )

    async def _fake_get_active(self, user_id, opportunity_id):
        return existing

    async def _get_db_session() -> AsyncMock:
        return AsyncMock()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(DealRepository, "get_active_by_opportunity", _fake_get_active)
        app.dependency_overrides[get_db_session] = _get_db_session

        response = client.post("/api/v1/deals", json={"opportunity_id": "opp-1"})
        assert response.status_code == 409
        body = response.json()
        # El handler de excepciones envuelve el detail en un objeto {error: {...}}.
        assert body["error"]["code"] == "conflict"
        assert "active deal" in body["error"]["message"].lower()


# ---------------------------------------------------------------------------
# GET /deals + filtro de estado validado
# ---------------------------------------------------------------------------


def test_list_deals_returns_shape(auth_override: None) -> None:
    """GET /deals -> 200 con shape items/total/limit/offset."""
    deal = _make_deal()

    async def _fake_list_for_user(self, **kwargs):
        return [deal], 1

    async def _get_db_session() -> AsyncMock:
        return AsyncMock()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(DealRepository, "list_for_user", _fake_list_for_user)
        app.dependency_overrides[get_db_session] = _get_db_session

        response = client.get("/api/v1/deals")
        assert response.status_code == 200
        data = response.json()
        assert {"items", "total", "limit", "offset"} <= set(data)
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == "NEW"


def test_list_deals_passes_status_filter(auth_override: None) -> None:
    """El filtro status se pasa al repo como enum."""
    captured: dict = {}

    async def _fake_list_for_user(self, **kwargs):
        captured.update(kwargs)
        return [], 0

    async def _get_db_session() -> AsyncMock:
        return AsyncMock()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(DealRepository, "list_for_user", _fake_list_for_user)
        app.dependency_overrides[get_db_session] = _get_db_session

        response = client.get("/api/v1/deals?status=NEW")
        assert response.status_code == 200
        assert captured.get("user_id") == "user-1"
        assert captured.get("status") == DealStatus.NEW


def test_list_deals_invalid_status_filter_returns_422(auth_override: None) -> None:
    """Filtro status inválido -> 422 (no se pasa crudo al repo)."""
    async def _get_db_session() -> AsyncMock:
        return AsyncMock()

    with pytest.MonkeyPatch.context() as mp:
        app.dependency_overrides[get_db_session] = _get_db_session
        response = client.get("/api/v1/deals?status=CONTACTED")
        assert response.status_code == 422
        assert "Invalid status filter" in response.json()["error"]["message"]


# ---------------------------------------------------------------------------
# PATCH /deals/{id}/status
# ---------------------------------------------------------------------------


def test_patch_status_valid_transition_returns_200(auth_override: None) -> None:
    """PATCH /deals/{id}/status NEW->ANALYZING -> 200."""
    deal = _make_deal(status=DealStatus.NEW)

    async def _fake_get_by_id(self, deal_id, *, for_update=False):
        return deal

    async def _fake_save_transition(self, deal_arg, history, audit_log=None):
        deal_arg.status = DealStatus.ANALYZING
        return deal_arg

    async def _get_db_session() -> AsyncMock:
        return AsyncMock()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(DealRepository, "get_by_id", _fake_get_by_id)
        mp.setattr(DealRepository, "save_transition", _fake_save_transition)
        app.dependency_overrides[get_db_session] = _get_db_session

        response = client.patch(
            "/api/v1/deals/deal-1/status",
            json={"status": "ANALYZING"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ANALYZING"


def test_patch_status_to_negotiating_saves_price(auth_override: None) -> None:
    """PATCH a NEGOTIATING con offer_price -> persistido."""
    deal = _make_deal(status=DealStatus.ANALYZING)

    async def _fake_get_by_id(self, deal_id, *, for_update=False):
        return deal

    async def _fake_save(self, deal_arg, history, audit_log=None):
        deal.status = DealStatus.NEGOTIATING
        deal.offer_price = 15000.0
        return deal

    async def _get_db_session() -> AsyncMock:
        return AsyncMock()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(DealRepository, "get_by_id", _fake_get_by_id)
        mp.setattr(DealRepository, "save_transition", _fake_save)
        app.dependency_overrides[get_db_session] = _get_db_session

        response = client.patch(
            "/api/v1/deals/deal-1/status",
            json={"status": "NEGOTIATING", "offer_price": 15000.0},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "NEGOTIATING"
        assert response.json()["offer_price"] == 15000.0


def test_patch_same_status_is_idempotent_200(auth_override: None) -> None:
    """PATCH al estado actual -> 200 idempotente, sin escritura."""
    deal = _make_deal(status=DealStatus.NEGOTIATING)

    async def _fake_get_by_id(self, deal_id, *, for_update=False):
        return deal

    async def _fake_save(self, *args, **kwargs):  # no debe llamarse
        raise AssertionError("save_transition no debe llamarse en no-op")

    async def _get_db_session() -> AsyncMock:
        return AsyncMock()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(DealRepository, "get_by_id", _fake_get_by_id)
        mp.setattr(DealRepository, "save_transition", _fake_save)
        app.dependency_overrides[get_db_session] = _get_db_session

        response = client.patch(
            "/api/v1/deals/deal-1/status",
            json={"status": "NEGOTIATING"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "NEGOTIATING"


def test_patch_status_illegal_returns_422(auth_override: None) -> None:
    """PATCH /deals/{id}/status con transición imposible (NEW->WON) -> 422."""
    deal = _make_deal(status=DealStatus.NEW)

    async def _fake_get_by_id(self, deal_id, *, for_update=False):
        return deal

    async def _get_db_session() -> AsyncMock:
        return AsyncMock()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(DealRepository, "get_by_id", _fake_get_by_id)
        app.dependency_overrides[get_db_session] = _get_db_session

        response = client.patch(
            "/api/v1/deals/deal-1/status",
            json={"status": "WON"},
        )
        assert response.status_code == 422


def test_patch_invalid_status_value_returns_422(auth_override: None) -> None:
    """Estado inexistente en el body -> 422 de pydantic."""
    async def _get_db_session() -> AsyncMock:
        return AsyncMock()

    with pytest.MonkeyPatch.context() as mp:
        app.dependency_overrides[get_db_session] = _get_db_session
        response = client.patch(
            "/api/v1/deals/deal-1/status",
            json={"status": "DROPPED"},
        )
        assert response.status_code == 422


def test_patch_negative_offer_price_returns_422(auth_override: None) -> None:
    """offer_price negativo -> 422."""
    async def _get_db_session() -> AsyncMock:
        return AsyncMock()

    with pytest.MonkeyPatch.context() as mp:
        app.dependency_overrides[get_db_session] = _get_db_session
        response = client.patch(
            "/api/v1/deals/deal-1/status",
            json={"status": "NEGOTIATING", "offer_price": -5},
        )
        assert response.status_code == 422


def test_patch_foreign_deal_returns_404(auth_override: None) -> None:
    """PATCH sobre deal ajeno -> 404."""
    deal = _make_deal(user_id="user-2", status=DealStatus.NEW)

    async def _fake_get_by_id(self, deal_id, *, for_update=False):
        return deal

    async def _get_db_session() -> AsyncMock:
        return AsyncMock()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(DealRepository, "get_by_id", _fake_get_by_id)
        app.dependency_overrides[get_db_session] = _get_db_session

        response = client.patch(
            "/api/v1/deals/deal-1/status",
            json={"status": "ANALYZING"},
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /deals/{id}/history (auditoría)
# ---------------------------------------------------------------------------


def test_get_history_requires_auth() -> None:
    """Sin token -> 401."""
    with patch.object(settings, "auth_disabled", False):
        response = client.get("/api/v1/deals/deal-1/history")
        assert response.status_code == 401


def test_get_history_returns_entries(auth_override: None) -> None:
    """GET history -> 200 con items del historial del deal propio."""
    deal = _make_deal()
    history = _make_history("deal-1")

    async def _fake_get_by_id(self, deal_id):
        return deal

    async def _fake_list_history(self, deal_id, *, limit=100, offset=0):
        return history, len(history)

    async def _get_db_session() -> AsyncMock:
        return AsyncMock()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(DealRepository, "get_by_id", _fake_get_by_id)
        mp.setattr(DealRepository, "list_history", _fake_list_history)
        app.dependency_overrides[get_db_session] = _get_db_session

        response = client.get("/api/v1/deals/deal-1/history")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        first = data["items"][0]
        assert first["from_status"] is None
        assert first["to_status"] == "NEW"
        second = data["items"][1]
        assert second["from_status"] == "NEW"
        assert second["to_status"] == "ANALYZING"


def test_get_history_foreign_deal_returns_404(auth_override: None) -> None:
    """Historial de un deal ajeno -> 404."""
    deal = _make_deal(user_id="user-2")

    async def _fake_get_by_id(self, deal_id):
        return deal

    async def _get_db_session() -> AsyncMock:
        return AsyncMock()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(DealRepository, "get_by_id", _fake_get_by_id)
        app.dependency_overrides[get_db_session] = _get_db_session

        response = client.get("/api/v1/deals/deal-1/history")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Task E.2 — PATCH /deals/{id}/simulation
# ---------------------------------------------------------------------------


def test_patch_simulation_requires_auth() -> None:
    """Sin token -> 401."""
    with patch.object(settings, "auth_disabled", False):
        response = client.patch(
            "/api/v1/deals/deal-1/simulation",
            json={"net_profit": 1000.0},
        )
        assert response.status_code == 401


def test_patch_simulation_ok_returns_200(auth_override: None) -> None:
    """PATCH /deals/{id}/simulation con deal propio -> 200 y campos guardados."""
    deal = _make_deal(status=DealStatus.NEW)

    async def _fake_get_by_id(self, deal_id):
        return deal

    async def _fake_update(self, deal: Deal) -> Deal:
        deal.last_sim_net_profit = 2500.0
        deal.last_sim_roi = 11.63
        deal.last_sim_profile = "SPAIN"
        return deal

    async def _get_db_session() -> AsyncMock:
        return AsyncMock()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(DealRepository, "get_by_id", _fake_get_by_id)
        mp.setattr(DealRepository, "update", _fake_update)
        app.dependency_overrides[get_db_session] = _get_db_session

        response = client.patch(
            "/api/v1/deals/deal-1/simulation",
            json={
                "purchase_price": 18000.0,
                "estimated_sale_price": 24000.0,
                "total_cost": 21500.0,
                "net_profit": 2500.0,
                "roi_percentage": 11.63,
                "profile_name": "SPAIN",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["last_sim_net_profit"] == 2500.0
        assert data["last_sim_roi"] == 11.63
        assert data["last_sim_profile"] == "SPAIN"
        # No cambia status.
        assert data["status"] == "NEW"


def test_patch_simulation_foreign_deal_returns_404(auth_override: None) -> None:
    """PATCH /deals/{id}/simulation sobre deal ajeno -> 404."""
    deal = _make_deal(user_id="user-2", status=DealStatus.NEW)

    async def _fake_get_by_id(self, deal_id):
        return deal

    async def _get_db_session() -> AsyncMock:
        return AsyncMock()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(DealRepository, "get_by_id", _fake_get_by_id)
        app.dependency_overrides[get_db_session] = _get_db_session

        response = client.patch(
            "/api/v1/deals/deal-1/simulation",
            json={"net_profit": 1000.0},
        )
        assert response.status_code == 404
