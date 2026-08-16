from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.user import User
from app.repositories.user_repository import UserRepository


def _aiosqlite_available() -> bool:
    try:
        import aiosqlite  # noqa: F401
        return True
    except ImportError:
        return False


requires_aiosqlite = pytest.mark.skipif(
    not _aiosqlite_available(),
    reason="aiosqlite/_sqlite3 not importable on this host (e.g. Windows AppLocker)",
)

pytestmark = requires_aiosqlite


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        async_session = sessionmaker(connection, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as s:
            yield s
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_and_get_by_id(session: AsyncSession) -> None:
    repo = UserRepository(session)
    user = User(email="user@example.com", hashed_password="secret")

    created = await repo.create(user)
    fetched = await repo.get_by_id(created.id)

    assert created.id is not None
    assert fetched is not None
    assert fetched.email == "user@example.com"


@pytest.mark.asyncio
async def test_get_by_email_and_list(session: AsyncSession) -> None:
    repo = UserRepository(session)
    user = User(email="another@example.com", hashed_password="secret")

    await repo.create(user)
    fetched = await repo.get_by_email("another@example.com")
    users = await repo.list()

    assert fetched is not None
    assert fetched.email == "another@example.com"
    assert len(users) == 1


@pytest.mark.asyncio
async def test_update_and_delete(session: AsyncSession) -> None:
    repo = UserRepository(session)
    user = User(email="update@example.com", hashed_password="secret")

    created = await repo.create(user)
    created.full_name = "Updated Name"
    updated = await repo.update(created)
    await repo.delete(updated)
    deleted = await repo.get_by_id(updated.id)

    assert updated.full_name == "Updated Name"
    assert deleted is None
