from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vehicle_evaluation import VehicleEvaluation


class VehicleEvaluationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, evaluation: VehicleEvaluation) -> VehicleEvaluation:
        self.session.add(evaluation)
        await self.session.commit()
        await self.session.refresh(evaluation)
        return evaluation

    async def get_by_id(self, evaluation_id: str | UUID) -> VehicleEvaluation | None:
        result = await self.session.execute(
            select(VehicleEvaluation).where(VehicleEvaluation.id == str(evaluation_id))
        )
        return result.scalar_one_or_none()

    async def get_by_vehicle_id(self, vehicle_id: str | UUID) -> VehicleEvaluation | None:
        result = await self.session.execute(
            select(VehicleEvaluation).where(VehicleEvaluation.vehicle_id == str(vehicle_id))
        )
        return result.scalar_one_or_none()

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[VehicleEvaluation]:
        result = await self.session.execute(
            select(VehicleEvaluation).order_by(VehicleEvaluation.created_at.desc(), VehicleEvaluation.id.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def update(self, evaluation: VehicleEvaluation) -> VehicleEvaluation:
        await self.session.commit()
        await self.session.refresh(evaluation)
        return evaluation

    async def delete(self, evaluation: VehicleEvaluation) -> None:
        await self.session.delete(evaluation)
        await self.session.commit()