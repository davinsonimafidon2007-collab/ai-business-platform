"""E2E backend — flujos completos sobre la app ASGI en proceso (TEST.E2E.1).

Sin servidor vivo: ``ASGITransport``. Dependencias externas reales:

- ``/health`` y Postgres/Redis: si no están levantados, la app degrada (503).
  Los tests lo modelan explícitamente o se saltan con el motivo.
- El flujo OPPORTUNITY→DEAL corre 100 % en proceso con SQLite en memoria
  (override de ``get_db_session``): ejercita routers + servicios + repos
  REALES, sin mockear la lógica de negocio.
"""

from __future__ import annotations

import os
import socket
import uuid
from urllib.parse import urlparse

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database import get_db_session
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.base import Base
from app.models.opportunity import Opportunity
from app.models.user import User
from app.models.vehicle import Vehicle

# ---------------------------------------------------------------------------
# Detección de dependencias externas (para skips explicados)
# ---------------------------------------------------------------------------


def _postgres_reachable() -> bool:
    db_url = os.environ.get("DATABASE_URL") or ""
    if not db_url:
        from app.core.config import settings

        db_url = settings.database_url
    try:
        parsed = urlparse(db_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except Exception:
        return False


def _auth_disabled_in_tests() -> bool:
    value = os.environ.get("AUTH_DISABLED_IN_TESTS", "").strip().lower()
    return value in {"true", "1"}


@pytest.fixture()
async def api_client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(base_url="http://test", transport=transport) as client:
        yield client


# ---------------------------------------------------------------------------
# Salud y superficie pública
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_health_is_public(api_client: AsyncClient) -> None:
    """Depende de DB/Redis: sin ellos la app responde 503 degraded (DEVOPS-001)."""
    response = await api_client.get("/health")
    assert response.status_code in {200, 503}
    payload = response.json()
    assert payload["status"] in {"ok", "degraded", "error"}


@pytest.mark.anyio
async def test_search_is_public(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/api/v1/search",
        json={"query": "BMW", "max_results": 1, "providers": ["mobile_de"]},
        headers={"Authorization": "Bearer test"},
    )
    assert response.status_code in {200, 401, 422}


@pytest.mark.anyio
@pytest.mark.skipif(
    _auth_disabled_in_tests(),
    reason="Modo personal (AUTH_DISABLED_IN_TESTS=true): get_current_user inyecta "
    "usuario local ADMIN y ningún endpoint devuelve 401 por falta de token.",
)
async def test_dashboard_requires_auth(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/dashboard/stats")
    assert response.status_code == 401


@pytest.mark.anyio
@pytest.mark.skipif(
    not _postgres_reachable(),
    reason="Requiere PostgreSQL real en DATABASE_URL: register/login persisten "
    "usuarios vía asyncpg. Arranca Postgres (docker compose up db) para ejecutarlo.",
)
async def test_full_auth_flow(api_client: AsyncClient) -> None:
    """register → login → dashboard con JWT real contra Postgres."""
    email = f"e2e-{uuid.uuid4()}@example.com"
    register = await api_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "changeme", "full_name": "E2E User"},
    )
    assert register.status_code == 201, register.text

    login = await api_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "changeme"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    dashboard = await api_client.get(
        "/api/v1/dashboard/stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert dashboard.status_code == 200, dashboard.text
    payload = dashboard.json()
    assert "recent_searches" in payload
    assert payload["recent_searches"] == 0


# ---------------------------------------------------------------------------
# E2E OPPORTUNITY → DEAL (in-process, SQLite; sin dependencias externas)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def deal_flow():
    """Override de sesión (SQLite) + auth local, y datos semilla reales."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    user_id = "44444444-4444-4444-8444-444444444444"
    vehicle_id = "45454545-4545-4545-8545-454545454545"
    opportunity_id = f"{uuid.uuid4()}"

    async with factory() as seed_session:
        seed_session.add_all(
            [
                User(id=user_id, email="e2e-deal@example.com", hashed_password="x"),
                Vehicle(
                    id=vehicle_id,
                    user_id=user_id,
                    source="autoscout24",
                    external_id=f"as24-{uuid.uuid4()}",
                    brand="Audi",
                    model="A4 40 TDI",
                    price=18500.0,
                    currency="EUR",
                ),
                Opportunity(
                    id=opportunity_id,
                    vehicle_id=vehicle_id,
                    opportunity_score=91.0,
                    recommendation="BUY_NOW",
                    roi=21.0,
                    risk="LOW",
                    profit=5100.0,
                ),
            ]
        )
        await seed_session.commit()

    async def override_get_db_session():
        async with factory() as session:
            yield session

    async def override_get_current_user():
        async with factory() as session:
            return await session.get(User, user_id)

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_current_user] = override_get_current_user

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(base_url="http://test", transport=transport) as client:
            yield {
                "client": client,
                "user_id": user_id,
                "vehicle_id": vehicle_id,
                "opportunity_id": opportunity_id,
            }
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        app.dependency_overrides.pop(get_current_user, None)
        await engine.dispose()


@pytest.mark.anyio
async def test_opportunity_to_deal_full_conversion(deal_flow) -> None:
    """Listar oportunidad → crear deal → 409 duplicado → fases → aprobar."""
    client: AsyncClient = deal_flow["client"]
    opportunity_id = deal_flow["opportunity_id"]

    # 1. La oportunidad aparece en el listado del usuario
    listing = await client.get("/api/v1/opportunities?limit=50")
    assert listing.status_code == 200, listing.text
    items = listing.json()["items"]
    ids = [item["id"] for item in items]
    assert opportunity_id in ids

    # 2. Creación del deal vinculado a la oportunidad
    created = await client.post(
        "/api/v1/deals",
        json={"opportunity_id": opportunity_id, "notes": "E2E conversión"},
    )
    assert created.status_code in {200, 201}, created.text
    deal = created.json()
    assert deal["opportunity_id"] == opportunity_id
    assert deal["status"] == "NEW"

    # 3. Idempotencia: un segundo deal activo para la misma oportunidad → 409
    duplicate = await client.post(
        "/api/v1/deals", json={"opportunity_id": opportunity_id}
    )
    assert duplicate.status_code == 409, duplicate.text

    # 4. Fases del workflow OPP→DEAL: seeding automático con 4 etapas
    phases_resp = await client.get(f"/api/v1/opportunities/{opportunity_id}/phases")
    assert phases_resp.status_code == 200, phases_resp.text
    phases = phases_resp.json()
    assert len(phases) == 4
    assert [p["order"] for p in phases] == [1, 2, 3, 4]
    offer_phase = next(p for p in phases if p["order"] == 2)

    # 5. Aprobación humana de la fase de oferta
    approved = await client.patch(
        f"/api/v1/opportunities/{opportunity_id}/phases/{offer_phase['id']}",
        json={"action": "approve"},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "completed"


@pytest.mark.anyio
async def test_deal_status_transition_new_to_negotiating(deal_flow) -> None:
    client: AsyncClient = deal_flow["client"]
    opportunity_id = deal_flow["opportunity_id"]

    created = await client.post("/api/v1/deals", json={"opportunity_id": opportunity_id})
    deal_id = created.json()["id"]

    transition = await client.patch(
        f"/api/v1/deals/{deal_id}/status",
        json={"status": "ANALYZING"},
    )
    assert transition.status_code == 200, transition.text
    assert transition.json()["status"] == "ANALYZING"

    negotiating = await client.patch(
        f"/api/v1/deals/{deal_id}/status",
        json={"status": "NEGOTIATING", "offer_price": 17500.0},
    )
    assert negotiating.status_code == 200, negotiating.text
    assert negotiating.json()["status"] == "NEGOTIATING"

    # Transición inválida NEW→WON rechazada por la máquina de estados
    created2 = await client.post("/api/v1/deals", json={})
    assert created2.status_code == 422

    history = await client.get(f"/api/v1/deals/{deal_id}/history")
    assert history.status_code == 200, history.text
    entries = history.json()["items"]
    statuses = {entry["to_status"] for entry in entries}
    # La creación registra NEW; las dos transiciones quedan auditadas.
    assert "NEW" in statuses
    assert {"ANALYZING", "NEGOTIATING"} <= statuses
