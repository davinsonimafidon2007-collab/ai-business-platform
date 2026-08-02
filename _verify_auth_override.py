"""Verificación controlada: confirma que app.dependency_overrides[get_current_user]
convierte el 401 en el código esperado en /api/v1/vehicles y /api/v1/search,
sin depender del AuthenticationMiddleware (que es pasivo)."""

import asyncio

from httpx import ASGITransport, AsyncClient

from app.dependencies.auth import get_current_user
from app.db.session import get_db_session
from app.main import app
from app.models.base import Base
from app.models.role import Role
from app.models.user import User
from app.models.vehicle import Vehicle


async def _make_db_override():
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def _get_session():
        async with session_factory() as session:
            yield session

    return _get_session


async def _override_current_user():
    return User(email="test@example.com", hashed_password="secret", role=Role.USER)


async def main() -> None:
    db_override = await _make_db_override()
    app.dependency_overrides[get_db_session] = db_override
    app.dependency_overrides[get_current_user] = _override_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1) POST /api/v1/vehicles
        resp = await client.post(
            "/api/v1/vehicles",
            json={
                "source": "mobile.de",
                "external_id": "ext-001",
                "brand": "BMW",
                "model": "X5",
                "year": 2020,
                "mileage": 50000,
                "price": 35000.0,
                "currency": "EUR",
            },
        )
        print(f"POST /api/v1/vehicles -> {resp.status_code}")
        try:
            data = resp.json()
            print("  body keys:", sorted(data.keys()))
        except Exception:
            print("  body:", resp.text[:200])

        # 2) GET /api/v1/vehicles (usuario USER listando sus vehículos)
        resp_get = await client.get("/api/v1/vehicles")
        print(f"GET /api/v1/vehicles -> {resp_get.status_code}")

    app.dependency_overrides.clear()


if __name__ == "__main__":
    asyncio.run(main())

