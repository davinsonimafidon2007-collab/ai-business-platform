from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vehicle import Vehicle


class VehicleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, vehicle: Vehicle) -> Vehicle:
        self.session.add(vehicle)
        await self.session.commit()
        await self.session.refresh(vehicle)
        return vehicle

    async def get_by_id(self, vehicle_id: str | UUID) -> Vehicle | None:
        result = await self.session.execute(select(Vehicle).where(Vehicle.id == str(vehicle_id)))
        return result.scalar_one_or_none()

    async def get_by_external_id(self, source: str, external_id: str) -> Vehicle | None:
        result = await self.session.execute(
            select(Vehicle).where(Vehicle.source == source, Vehicle.external_id == external_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[Vehicle]:
        result = await self.session.execute(select(Vehicle).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def update(self, vehicle: Vehicle) -> Vehicle:
        await self.session.commit()
        await self.session.refresh(vehicle)
        return vehicle

    async def delete(self, vehicle: Vehicle) -> None:
        await self.session.delete(vehicle)
        await self.session.commit()