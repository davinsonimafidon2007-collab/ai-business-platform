"""Tests de la API de deals (Task D.1): auth, create, list, status."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.database import get_db_session
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.deal import Deal, DealStatus
from app.models.user import User
from app.repositories.deal_repository import DealRepository

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
    response = client.get("/api/v1/deals")
    assert response.status_code == 401


def test_create_deal_returns_201(auth_override: None) -> None:
    """POST /deals con auth -> 201 y status NEW."""
    deal = _make_deal()

    async def _fake_create(self, deal: Deal) -> Deal:
        return deal

    async def _fake_get_active(self, user_id, opportunity_id):
        return None

    async def _get_db_session() -> AsyncMock:
        session = AsyncMock()
        return session

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(DealRepository, "create", _fake_create)
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


def test_create_deal_without_link_returns_422(auth_override: None) -> None:
    """POST /deals sin opportunity ni vehicle -> 422."""
    async def _get_db_session() -> AsyncMock:
        return AsyncMock()

    with pytest.MonkeyPatch.context() as mp:
        app.dependency_overrides[get_db_session] = _get_db_session
        response = client.post("/api/v1/deals", json={"notes": "sin vinculo"})
        assert response.status_code == 422


def test_create_duplicate_active_returns_409(auth_override: None) -> None:
    """POST /deals con opportunity con deal activo -> 409 (Task D.3)."""
    existing = _make_deal(
        deal_id="deal-existing", status=DealStatus.OFFER, opportunity_id="opp-1"
    )

    async def _fake_get_active(self, user_id, opportunity_id):
        return existing

    async def _get_db_session() -> AsyncMock:
        return AsyncMock()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(DealRepository, "get_active_by_opportunity", _fake_get_active)
        app.dependency_overrides[get_db_session] = _get_db_session

        response = client.post(
            "/api/v1/deals", json={"opportunity_id": "opp-1"}
        )
        assert response.status_code == 409
        body = response.json()
        # El handler de excepciones envuelve el detail en un objeto {error: {...}}.
        assert body["error"]["code"] == "conflict"
        assert "active deal" in body["error"]["message"].lower()


def test_patch_status_to_offer_saves_price(auth_override: None) -> None:
    """PATCH a OFFER con offer_price -> persistido (Task D.3)."""
    deal = _make_deal(status=DealStatus.CONTACTED)

    async def _fake_get_by_id(self, deal_id):
        return deal

    async def _fake_update(self, deal: Deal) -> Deal:
        deal.status = DealStatus.OFFER
        deal.offer_price = 15000.0
        return deal

    async def _get_db_session() -> AsyncMock:
        return AsyncMock()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(DealRepository, "get_by_id", _fake_get_by_id)
        mp.setattr(DealRepository, "update", _fake_update)
        app.dependency_overrides[get_db_session] = _get_db_session

        response = client.patch(
            "/api/v1/deals/deal-1/status",
            json={"status": "OFFER", "offer_price": 15000.0},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "OFFER"
        assert response.json()["offer_price"] == 15000.0


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
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == "NEW"


def test_list_deals_passes_status_filter(auth_override: None) -> None:
    """El filtro status se pasa al repo."""
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
        assert captured.get("status") is not None


def test_patch_status_illegal_returns_422(auth_override: None) -> None:
    """PATCH /deals/{id}/status con transición ilegal -> 422."""
    deal = _make_deal(status=DealStatus.NEW)

    async def _fake_get_by_id(self, deal_id):
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


def test_patch_status_ok_returns_200(auth_override: None) -> None:
    """PATCH /deals/{id}/status con transición válida -> 200."""
    deal = _make_deal(status=DealStatus.NEW)

    async def _fake_get_by_id(self, deal_id):
        return deal

    async def _fake_update(self, deal: Deal) -> Deal:
        deal.status = DealStatus.CONTACTED
        return deal

    async def _get_db_session() -> AsyncMock:
        return AsyncMock()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(DealRepository, "get_by_id", _fake_get_by_id)
        mp.setattr(DealRepository, "update", _fake_update)
        app.dependency_overrides[get_db_session] = _get_db_session

        response = client.patch(
            "/api/v1/deals/deal-1/status",
            json={"status": "CONTACTED"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "CONTACTED"


# ---------------------------------------------------------------------------
# Task E.2 — PATCH /deals/{id}/simulation
# ---------------------------------------------------------------------------


def test_patch_simulation_requires_auth() -> None:
    """Sin token -> 401."""
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
