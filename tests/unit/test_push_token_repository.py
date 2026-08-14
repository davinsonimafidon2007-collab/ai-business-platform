from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.user import User
from app.repositories.push_token_repository import PushTokenRepository


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
async def test_upsert_creates_token(session: AsyncSession) -> None:
    repo = PushTokenRepository(session)
    user = User(email="push@example.com", hashed_password="secret")
    session.add(user)
    await session.commit()

    push_token = await repo.upsert(
        user_id=user.id,
        token="fcm-token-1",
        platform="android",
    )

    assert push_token.id is not None
    assert push_token.token == "fcm-token-1"
    assert push_token.platform == "android"
    assert push_token.user_id == user.id


@pytest.mark.asyncio
async def test_upsert_updates_existing_token(session: AsyncSession) -> None:
    repo = PushTokenRepository(session)
    user = User(email="push@example.com", hashed_password="secret")
    session.add(user)
    await session.commit()

    first = await repo.upsert(user_id=user.id, token="fcm-token-1", platform="android")
    second = await repo.upsert(user_id=user.id, token="fcm-token-2", platform="android")

    assert first.id == second.id
    assert second.token == "fcm-token-2"
    tokens = await repo.get_by_user_id(user.id)
    assert len(tokens) == 1
    assert tokens[0].token == "fcm-token-2"


@pytest.mark.asyncio
async def test_upsert_separates_platforms(session: AsyncSession) -> None:
    repo = PushTokenRepository(session)
    user = User(email="push@example.com", hashed_password="secret")
    session.add(user)
    await session.commit()

    await repo.upsert(user_id=user.id, token="fcm-android", platform="android")
    await repo.upsert(user_id=user.id, token="fcm-ios", platform="ios")

    tokens = await repo.get_by_user_id(user.id)
    assert len(tokens) == 2
    assert {t.platform for t in tokens} == {"android", "ios"}
