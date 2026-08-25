from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.limits import clamp_limit
from app.models.audit_log import AuditLog
from app.models.deal import ACTIVE_STATUSES, Deal, DealStatus, DealStatusHistory


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

        Raises:
            sqlalchemy.exc.IntegrityError: si se viola el índice único parcial
                ``uq_deals_active_per_opportunity`` (duplicado concurrente).
        """
        self.session.add(deal)
        await self.session.commit()
        await self.session.refresh(deal)
        return deal

    async def get_by_id(
        self,
        deal_id: str | UUID,
        *,
        for_update: bool = False,
    ) -> Deal | None:
        """Retrieves a deal by id.

        Args:
            deal_id: The UUID (as string or UUID object) of the deal.
            for_update: Si True, bloquea la fila (SELECT ... FOR UPDATE)
                para serializar transiciones concurrentes. En SQLite el
                lock es un no-op; en PostgreSQL es real.

        Returns:
            The Deal if found, None otherwise.
        """
        query = (
            select(Deal)
            .where(Deal.id == str(deal_id))
            .options(
                selectinload(Deal.vehicle),
                selectinload(Deal.opportunity),
            )
        )
        if for_update:
            query = query.with_for_update()
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_active_by_opportunity(
        self,
        user_id: str | UUID,
        opportunity_id: str | UUID,
    ) -> Deal | None:
        """Returns an active deal (NEW|ANALYZING|NEGOTIATING) for an opportunity.

        Args:
            user_id: The owner of the deal.
            opportunity_id: The opportunity to check.

        Returns:
            The active Deal if found, None otherwise.
        """
        active_statuses = [s.value for s in ACTIVE_STATUSES]
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
            status: Optional status filter (e.g. "NEW", "ANALYZING").
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

    async def save_transition(
        self,
        deal: Deal,
        history: DealStatusHistory,
        audit_log: AuditLog | None = None,
    ) -> Deal:
        """Persists a state transition atomically.

        Deal + history + audit log se confirman en una única transacción:
        o queda todo, o no queda nada. Un conflicto de versión (bloqueo
        optimista) eleva ``StaleDataError`` desde el commit.

        Args:
            deal: The Deal instance with updated fields.
            history: The immutable DealStatusHistory row for this transition.
            audit_log: Optional AuditLog entry for the global audit trail.

        Returns:
            The refreshed Deal.
        """
        self.session.add(history)
        if audit_log is not None:
            self.session.add(audit_log)
        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        await self.session.refresh(deal)
        return deal

    async def list_history(
        self,
        deal_id: str | UUID,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[DealStatusHistory], int]:
        """Lists the status history of a deal, newest first.

        Args:
            deal_id: The deal whose history to list.
            limit: Maximum number of records to return.
            offset: Number of records to skip.

        Returns:
            A tuple of (list of DealStatusHistory, total count).
        """
        limit = clamp_limit(limit)
        deal_id_str = str(deal_id)

        count_result = await self.session.execute(
            select(func.count(DealStatusHistory.id)).where(
                DealStatusHistory.deal_id == deal_id_str
            )
        )
        total = count_result.scalar() or 0

        result = await self.session.execute(
            select(DealStatusHistory)
            .where(DealStatusHistory.deal_id == deal_id_str)
            .order_by(DealStatusHistory.created_at.desc(), DealStatusHistory.id.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list(result.scalars().all())
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

    async def delete(self, deal: Deal, audit_log: AuditLog | None = None) -> None:
        """Deletes a deal record (history cascades).

        Args:
            deal: The Deal instance to delete.
            audit_log: Optional AuditLog entry persisted in the same commit.
        """
        if audit_log is not None:
            self.session.add(audit_log)
        await self.session.delete(deal)
        await self.session.commit()

    @staticmethod
    def now() -> datetime:
        """Current aware UTC timestamp (helper shared with services)."""
        return datetime.now(UTC)
