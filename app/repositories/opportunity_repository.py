from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.opportunity import Opportunity
from app.models.vehicle import Vehicle


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

    async def list_filtered(
        self,
        *,
        user_id: str | None = None,
        recommendation: str | None = None,
        min_score: float | None = None,
        min_roi: float | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Opportunity], int]:
        """Lists opportunity records with optional filters and pagination.

        Opportunities are scoped to the user via the vehicle's ``user_id``.
        Returns ``(items, total)`` where items are ordered by
        ``opportunity_score`` DESC.

        Args:
            user_id: If provided, only opportunities for vehicles owned by
                this user are returned.
            recommendation: Optional filter on recommendation value
                (e.g. BUY_NOW, WATCH, NEGOTIATE, REJECT).
            min_score: Optional minimum opportunity_score (inclusive).
            min_roi: Optional minimum roi percentage (inclusive).
            limit: Maximum number of records to return.
            offset: Number of records to skip.

        Returns:
            A tuple of (list of Opportunity, total count).
        """
        base_query = select(Opportunity).join(
            Vehicle, Vehicle.id == Opportunity.vehicle_id
        )

        if user_id is not None:
            base_query = base_query.where(Vehicle.user_id == user_id)
        if recommendation is not None:
            base_query = base_query.where(Opportunity.recommendation == recommendation)
        if min_score is not None:
            base_query = base_query.where(Opportunity.opportunity_score >= min_score)
        if min_roi is not None:
            base_query = base_query.where(Opportunity.roi >= min_roi)

        # Count query
        count_query = select(func.count(Opportunity.id)).select_from(
            base_query.subquery()
        )
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Items query
        items_query = (
            base_query.order_by(Opportunity.opportunity_score.desc())
            .offset(offset)
            .limit(limit)
        )
        items_result = await self.session.execute(items_query)
        items = list(items_result.scalars().all())

        return items, total

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

