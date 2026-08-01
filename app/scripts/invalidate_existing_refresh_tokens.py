"""Script para invalidar todos los refresh tokens existentes.

Tras hashear los refresh tokens en el servicio (SHA-256), los tokens ya
guardados en texto plano nunca coincidirán con el hash recalculado.
Este script los marca como revocados para que los usuarios tengan que
volver a hacer login.

Ejecutar una sola vez después de desplegar el cambio:
    python -m app.scripts.invalidate_existing_refresh_tokens
"""

from __future__ import annotations

import asyncio

from app.core.config import settings


async def main() -> None:
    import asyncpg

    # settings.database_url es "postgresql+asyncpg://..."
    # asyncpg necesita "postgresql://..."
    url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")

    conn = await asyncpg.connect(url)
    try:
        result = await conn.execute("UPDATE refresh_tokens SET is_revoked = true")
        print(f"Refresh tokens invalidados: {result}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())