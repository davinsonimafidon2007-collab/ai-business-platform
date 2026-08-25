from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.limits import clamp_limit, clamp_skip
from app.models.vehicle import Vehicle
from app.repositories.cursor_pagination import CursorPaginator


class VehicleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, vehicle: Vehicle) -> Vehicle:
        self.session.add(vehicle)
        await self.session.commit()
        await self.session.refresh(vehicle)
        return vehicle

    async def get_by_id(self, vehicle_id: str | UUID) -> Vehicle | None:
        result = await self.session.execute(
            select(Vehicle)
            .where(Vehicle.id == str(vehicle_id))
            .options(
                selectinload(Vehicle.evaluations),
                selectinload(Vehicle.opportunities),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_external_id(self, source: str, external_id: str, user_id: str | None = None) -> Vehicle | None:
        query = select(Vehicle).where(Vehicle.source == source, Vehicle.external_id == external_id)
        if user_id is not None:
            query = query.where(Vehicle.user_id == str(user_id))
        query = query.options(selectinload(Vehicle.evaluations), selectinload(Vehicle.opportunities))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_vin(
        self,
        vin: str,
        user_id: str | None = None,
    ) -> Vehicle | None:
        """Localiza un vehículo por VIN normalizado (mayúsculas), opcionalmente
        acotado al usuario (TASK-017)."""
        normalized = (vin or "").strip().upper()
        query = select(Vehicle).where(Vehicle.vin == normalized)
        if user_id is not None:
            query = query.where(Vehicle.user_id == str(user_id))
        query = query.options(selectinload(Vehicle.evaluations), selectinload(Vehicle.opportunities))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[Vehicle]:
        skip = clamp_skip(skip)
        limit = clamp_limit(limit)
        result = await self.session.execute(
            select(Vehicle).order_by(Vehicle.created_at.desc(), Vehicle.id.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_user(self, user_id: str, skip: int = 0, limit: int = 100) -> list[Vehicle]:
        skip = clamp_skip(skip)
        limit = clamp_limit(limit)
        result = await self.session.execute(
            select(Vehicle)
            .where(Vehicle.user_id == str(user_id))
            .order_by(Vehicle.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_user(self, user_id: str) -> int:
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count(Vehicle.id)).where(Vehicle.user_id == str(user_id))
        )
        return result.scalar() or 0

    async def list_cursor(
        self,
        user_id: str,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[list[Vehicle], int, bool, str | None]:
        """Pagina los vehículos del usuario con keyset (TASK-019).

        Devuelve ``(items, total, has_more, next_cursor)`` ordenado por
        ``created_at DESC, id DESC``.
        """
        limit = clamp_limit(limit)
        paginator = CursorPaginator(self.session, Vehicle)
        return await paginator.paginate(
            cursor,
            limit,
            where=[Vehicle.user_id == str(user_id)],
        )

    async def update(self, vehicle: Vehicle) -> Vehicle:
        await self.session.commit()
        await self.session.refresh(vehicle)
        return vehicle

    async def delete(self, vehicle: Vehicle) -> None:
        await self.session.delete(vehicle)
        await self.session.commit()