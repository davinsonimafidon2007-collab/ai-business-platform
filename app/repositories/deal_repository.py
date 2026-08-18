from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.limits import clamp_limit
from app.models.deal import Deal, DealStatus


class DealRepository:
    """Repository for Deal persistence operations (Task D.1)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, deal: Deal) -> Deal:
        """Persists a new deal.

        Args:
            deal: The Deal instance to persist.

        Returns:
            The persisted Deal with generated id and timestamps.
        """
        self.session.add(deal)
        await self.session.commit()
        await self.session.refresh(deal)
        return deal

    async def get_by_id(self, deal_id: str | UUID) -> Deal | None:
        """Retrieves a deal by id.

        Args:
            deal_id: The UUID (as string or UUID object) of the deal.

        Returns:
            The Deal if found, None otherwise.
        """
        result = await self.session.execute(
            select(Deal)
            .where(Deal.id == str(deal_id))
            .options(
                selectinload(Deal.vehicle),
                selectinload(Deal.opportunity),
            )
        )
        return result.scalar_one_or_none()

    async def get_active_by_opportunity(
        self,
        user_id: str | UUID,
        opportunity_id: str | UUID,
    ) -> Deal | None:
        """Returns an active deal (NEW|CONTACTED|OFFER) for an opportunity.

        Args:
            user_id: The owner of the deal.
            opportunity_id: The opportunity to check.

        Returns:
            The active Deal if found, None otherwise.
        """
        active_statuses = [
            DealStatus.NEW.value,
            DealStatus.CONTACTED.value,
            DealStatus.OFFER.value,
        ]
        result = await self.session.execute(
            select(Deal).where(
                Deal.user_id == str(user_id),
                Deal.opportunity_id == str(opportunity_id),
                Deal.status.in_(active_statuses),
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        *,
        user_id: str | UUID,
        status: DealStatus | str | None = None,
        opportunity_id: str | UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Deal], int]:
        """Lists deals owned by a user, optionally filtered by status.

        Args:
            user_id: The owner of the deals.
            status: Optional status filter (e.g. "NEW", "CONTACTED").
            opportunity_id: Optional filter by opportunity.
            limit: Maximum number of records to return.
            offset: Number of records to skip.

        Returns:
            A tuple of (list of Deal, total count).
        """
        limit = clamp_limit(limit)
        base_query = select(Deal).where(Deal.user_id == str(user_id))

        if opportunity_id is not None:
            base_query = base_query.where(
                Deal.opportunity_id == str(opportunity_id)
            )

        if status is not None:
            status_value = (
                status.value if isinstance(status, DealStatus) else str(status)
            )
            base_query = base_query.where(Deal.status == status_value)

        count_query = select(func.count(Deal.id)).select_from(base_query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        items_query = (
            base_query.options(
                selectinload(Deal.vehicle),
                selectinload(Deal.opportunity),
            )
            .order_by(Deal.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items_result = await self.session.execute(items_query)
        items = list(items_result.scalars().all())

        return items, total

    async def update(self, deal: Deal) -> Deal:
        """Persists changes to an existing deal.

        Args:
            deal: The Deal instance with updated fields.

        Returns:
            The refreshed Deal.
        """
        await self.session.commit()
        await self.session.refresh(deal)
        return deal

    async def delete(self, deal: Deal) -> None:
        """Deletes a deal record.

        Args:
            deal: The Deal instance to delete.
        """
        await self.session.delete(deal)
        await self.session.commit()
