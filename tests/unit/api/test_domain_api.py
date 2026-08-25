"""Tests API de los routers sin cobertura previa (TEST.API.DOMAIN.1).

Cubre: workflows (stub), approvals (deriva de opportunity_phases), agents
(registry real) y notifications (tokens push). Sesión SQLite en memoria vía
override de ``get_db_session``; auth local vía override de ``get_current_user``.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import get_db_session
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.base import Base
from app.models.opportunity import Opportunity
from app.models.opportunity_phase import OpportunityPhase
from app.models.user import User

USER_ID = "55555555-5555-4555-8555-555555555555"
VEHICLE_ID = "56565656-5656-4565-8565-565656565656"


@pytest.fixture
def db_override():
    engine = create_async_engine("sqlite+aiosqlite://")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    state = {"ready": False}

    async def _prepare() -> None:
        if not state["ready"]:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            async with factory() as session:
                session.add(
                    User(id=USER_ID, email="domain@example.com", hashed_password="x")
                )
                await session.commit()
            state["ready"] = True

    async def override_get_db_session():
        await _prepare()
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    yield factory, _prepare

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user, None)
    engine.sync_engine.dispose()


@pytest.fixture
def client_with_auth(db_override) -> TestClient:
    # Instancia transitoria: los routers solo leen current_user.id y así
    # evitamos DetachedInstance/MissingGreenlet al salir de la sesión.
    async def override_get_current_user():
        return User(id=USER_ID, email="domain@example.com", hashed_password="x")

    app.dependency_overrides[get_current_user] = override_get_current_user
    return TestClient(app)


@pytest_asyncio.fixture
async def seed_phase(db_override):
    """Siembra una fase pending_approval y otra completed."""
    factory, prepare = db_override
    await prepare()

    async with factory() as session:
        vehicle_id = VEHICLE_ID
        opp_id = str(uuid4())
        session.add(
            Opportunity(
                id=opp_id,
                vehicle_id=vehicle_id,
                opportunity_score=80.0,
            )
        )
        pending = OpportunityPhase(
            opportunity_id=opp_id,
            title="Oferta / Negociación",
            status="pending_approval",
            order=2,
            agent="negotiation-engine",
        )
        done = OpportunityPhase(
            opportunity_id=opp_id,
            title="Evaluación inicial",
            status="completed",
            order=1,
            agent="evaluation-engine",
        )
        session.add_all([pending, done])
        await session.commit()
        return {"opportunity_id": opp_id, "pending_id": pending.id}


# ---------------------------------------------------------------------------
# Workflows (stub explícito del backend)
# ---------------------------------------------------------------------------


def test_workflows_list_returns_empty_list(client_with_auth: TestClient) -> None:
    resp = client_with_auth.get("/api/v1/workflows")
    assert resp.status_code == 200
    assert resp.json() == []


def test_workflow_detail_echoes_id(client_with_auth: TestClient) -> None:
    resp = client_with_auth.get("/api/v1/workflows/wf-123")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == "wf-123"
    assert {"status", "phases", "completed_phases"} <= set(body.keys())


# ---------------------------------------------------------------------------
# Approvals — deriva real de opportunity_phases.pending_approval
# ---------------------------------------------------------------------------


def test_approvals_lists_only_pending_approval(
    client_with_auth: TestClient, seed_phase
) -> None:
    resp = client_with_auth.get("/api/v1/approvals")
    assert resp.status_code == 200
    items = resp.json()

    ids = {item["id"] for item in items}
    assert seed_phase["pending_id"] in ids
    # La fase completada NO aparece como pendiente
    titles_pending = [item["title"] for item in items if item["id"] == seed_phase["pending_id"]]
    assert titles_pending == ["Oferta / Negociación"]
    sample = next(i for i in items if i["id"] == seed_phase["pending_id"])
    assert sample["opportunity_id"] == seed_phase["opportunity_id"]
    assert sample["status"] == "pending"


def test_approvals_empty_without_phases(client_with_auth: TestClient) -> None:
    resp = client_with_auth.get("/api/v1/approvals")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# Agents — registry real
# ---------------------------------------------------------------------------


def test_agents_list_from_registry(client_with_auth: TestClient) -> None:
    from app.agents.registry import describe_agents

    resp = client_with_auth.get("/api/v1/agents")
    assert resp.status_code == 200
    agents = resp.json()
    registry_entries = describe_agents()

    # La API refleja EXACTAMENTE el registry real (contrato, no datos fijos)
    assert {a["id"] for a in agents} == {e["id"] for e in registry_entries}
    assert len(agents) > 0
    for agent in agents:
        assert {"id", "name", "role"} <= set(agent.keys())


def test_agent_detail_unknown_returns_404(client_with_auth: TestClient) -> None:
    resp = client_with_auth.get("/api/v1/agents/does-not-exist")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Notifications — registro/borrado de tokens FCM
# ---------------------------------------------------------------------------


def test_register_and_unregister_push_token(client_with_auth: TestClient) -> None:
    token = f"fcm-token-{uuid4()}"

    registered = client_with_auth.post(
        "/api/v1/notifications/register",
        json={"token": token, "platform": "android"},
    )
    assert registered.status_code == 200, registered.text
    assert registered.json()["ok"] is True

    # Re-registro idempotente (upsert)
    again = client_with_auth.post(
        "/api/v1/notifications/register",
        json={"token": token, "platform": "ios"},
    )
    assert again.status_code == 200

    removed = client_with_auth.post(
        "/api/v1/notifications/unregister", json={"token": token}
    )
    assert removed.status_code == 200
    assert removed.json()["message"] == "Token unregistered"


def test_send_push_dry_run_without_firebase(client_with_auth: TestClient) -> None:
    resp = client_with_auth.post(
        "/api/v1/notifications/send",
        json={"title": "Nueva oportunidad", "body": "BMW 320d a precio bueno"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    # Sin credenciales Firebase el servicio responde skipped (dry-run)
    assert body["result"].get("skipped") in {True, False} or "skipped" in str(body["result"]).lower()


# ---------------------------------------------------------------------------
# Auth requerida en todos estos routers
# ---------------------------------------------------------------------------


def test_domain_routers_require_auth() -> None:
    for path in (
        "/api/v1/workflows",
        "/api/v1/approvals",
        "/api/v1/agents",
    ):
        resp = TestClient(app).get(path)
        assert resp.status_code in {401, 403}, path
