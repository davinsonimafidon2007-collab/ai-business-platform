from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.opportunity import Opportunity


class OpportunityRepository:
    """Repository for Opportunity persistence operations.

    Handles CRUD for vehicle import opportunity analysis records,
    including opportunity scores, recommendations, ROI, risk and profit data.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, opportunity: Opportunity) -> Opportunity:
        """Persists a new opportunity record.

        Args:
            opportunity: The Opportunity instance to persist.

        Returns:
            The persisted Opportunity with generated id and timestamps.
        """
        self.session.add(opportunity)
        await self.session.commit()
        await self.session.refresh(opportunity)
        return opportunity

    async def save_many(self, opportunities: list[Opportunity]) -> list[Opportunity]:
        """Persists multiple opportunity records in a single transaction.

        Args:
            opportunities: List of Opportunity instances to persist.

        Returns:
            List of persisted Opportunity instances.
        """
        for opp in opportunities:
            self.session.add(opp)
        await self.session.commit()
        for opp in opportunities:
            await self.session.refresh(opp)
        return opportunities

    async def get(self, opportunity_id: str | UUID) -> Opportunity | None:
        """Retrieves an opportunity record by id.

        Args:
            opportunity_id: The UUID (as string or UUID object) of the record.

        Returns:
            The Opportunity if found, None otherwise.
        """
        result = await self.session.execute(
            select(Opportunity).where(Opportunity.id == str(opportunity_id))
        )
        return result.scalar_one_or_none()

    async def get_by_vehicle_id(self, vehicle_id: str | UUID) -> list[Opportunity]:
        """Retrieves all opportunity records for a given vehicle.

        Args:
            vehicle_id: The UUID of the vehicle.

        Returns:
            List of Opportunity records ordered by analyzed_at DESC.
        """
        result = await self.session.execute(
            select(Opportunity)
            .where(Opportunity.vehicle_id == str(vehicle_id))
            .order_by(Opportunity.analyzed_at.desc())
        )
        return list(result.scalars().all())

    async def exists(self, vehicle_id: str | UUID) -> bool:
        """Checks if any opportunity record exists for a vehicle.

        Args:
            vehicle_id: The UUID of the vehicle.

        Returns:
            True if at least one record exists, False otherwise.
        """
        result = await self.session.execute(
            select(Opportunity.id)
            .where(Opportunity.vehicle_id == str(vehicle_id))
            .limit(1)
        )
        return result.scalar() is not None

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Opportunity]:
        """Lists all opportunity records with pagination.

        Args:
            skip: Number of records to skip (pagination).
            limit: Maximum number of records to return.

        Returns:
            List of Opportunity records ordered by created_at DESC.
        """
        result = await self.session.execute(
            select(Opportunity)
            .order_by(Opportunity.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def delete(self, opportunity: Opportunity) -> None:
        """Deletes an opportunity record.

        Args:
            opportunity: The Opportunity instance to delete.
        """
        await self.session.delete(opportunity)
        await self.session.commit()

    async def count(self) -> int:
        """Counts total opportunity records.

        Returns:
            Total number of records.
        """
        result = await self.session.execute(
            select(func.count(Opportunity.id))
        )
        return result.scalar() or 0

