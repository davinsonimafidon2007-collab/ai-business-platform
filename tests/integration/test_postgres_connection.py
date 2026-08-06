import asyncio

from sqlalchemy import text

from app.database import db_manager


def test_database_connection() -> None:
    async def _assert_connection() -> None:
        async with db_manager.engine.connect() as connection:
            result = await connection.execute(text("SELECT 1"))
            assert result.scalar_one() == 1

    asyncio.run(_assert_connection())
