import asyncio

from sqlalchemy import text

from app.db.session import engine


def test_database_connection() -> None:
    async def _assert_connection() -> None:
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT 1"))
            assert result.scalar_one() == 1

    asyncio.run(_assert_connection())
