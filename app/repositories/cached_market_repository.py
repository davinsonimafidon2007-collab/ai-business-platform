from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cached_market import CachedMarketData


class CachedMarketRepository:
    """Repository for CachedMarketData persistence operations.

    Handles CRUD for cached market estimation data.
    Cache entries are identified by (external_id, provider, market_hash)
    and have an expiration timestamp for TTL-based invalidation.

    This repository does NOT depend on vehicles table existence,
    allowing caching of market data before vehicle import.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, market_data: CachedMarketData) -> CachedMarketData:
        """Persists a new cached market data entry.

        Args:
            market_data: The CachedMarketData instance to persist.

        Returns:
            The persisted CachedMarketData with generated id and timestamps.
        """
        self.session.add(market_data)
        await self.session.commit()
        await self.session.refresh(market_data)
        return market_data

    async def save_many(
        self, market_data_list: list[CachedMarketData]
    ) -> list[CachedMarketData]:
        """Persists multiple cached market data entries in a single transaction.

        Args:
            market_data_list: List of CachedMarketData instances to persist.

        Returns:
            List of persisted CachedMarketData instances.
        """
        for md in market_data_list:
            self.session.add(md)
        await self.session.commit()
        for md in market_data_list:
            await self.session.refresh(md)
        return market_data_list

    async def get(self, market_data_id: str | UUID) -> CachedMarketData | None:
        """Retrieves a cached market data entry by id.

        Args:
            market_data_id: The UUID (as string or UUID object) of the record.

        Returns:
            The CachedMarketData if found, None otherwise.
        """
        result = await self.session.execute(
            select(CachedMarketData).where(
                CachedMarketData.id == str(market_data_id)
            )
        )
        return result.scalar_one_or_none()

    async def get_by_external_id(
        self,
        external_id: str,
        provider: str,
    ) -> list[CachedMarketData]:
        """Retrieves all cached market data for a given external vehicle.

        Args:
            external_id: The external vehicle identifier.
            provider: The provider name.

        Returns:
            List of CachedMarketData records ordered by created_at DESC.
        """
        result = await self.session.execute(
            select(CachedMarketData)
            .where(
                and_(
                    CachedMarketData.external_id == external_id,
                    CachedMarketData.provider == provider,
                )
            )
            .order_by(CachedMarketData.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_valid(
        self,
        external_id: str,
        provider: str,
        market_hash: str | None = None,
    ) -> CachedMarketData | None:
        """Retrieves a valid (non-expired) cached market data entry.

        Args:
            external_id: The external vehicle identifier.
            provider: The provider name.
            market_hash: Optional market hash to further filter the cache.

        Returns:
            The valid CachedMarketData if found (not expired), None otherwise.
        """
        now = datetime.now(timezone.utc)
        conditions = [
            CachedMarketData.external_id == external_id,
            CachedMarketData.provider == provider,
            or_(
                CachedMarketData.expires_at.is_(None),
                CachedMarketData.expires_at > now,
            ),
        ]
        if market_hash is not None:
            conditions.append(CachedMarketData.market_hash == market_hash)

        result = await self.session.execute(
            select(CachedMarketData)
            .where(and_(*conditions))
            .order_by(CachedMarketData.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def exists(
        self,
        external_id: str,
        provider: str,
        market_hash: str | None = None,
    ) -> bool:
        """Checks if a cached market data entry exists.

        Args:
            external_id: The external vehicle identifier.
            provider: The provider name.
            market_hash: Optional market hash to further filter.

        Returns:
            True if at least one matching record exists, False otherwise.
        """
        conditions = [
            CachedMarketData.external_id == external_id,
            CachedMarketData.provider == provider,
        ]
        if market_hash is not None:
            conditions.append(CachedMarketData.market_hash == market_hash)

        result = await self.session.execute(
            select(CachedMarketData.id)
            .where(and_(*conditions))
            .limit(1)
        )
        return result.scalar() is not None

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[CachedMarketData]:
        """Lists all cached market data entries with pagination.

        Args:
            skip: Number of records to skip (pagination).
            limit: Maximum number of records to return.

        Returns:
            List of CachedMarketData records ordered by created_at DESC.
        """
        result = await self.session.execute(
            select(CachedMarketData)
            .order_by(CachedMarketData.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def delete_expired(self) -> int:
        """Deletes all expired cached market data entries.

        Returns:
            Number of deleted records.
        """
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(CachedMarketData).where(
                CachedMarketData.expires_at < now
            )
        )
        expired = list(result.scalars().all())
        for entry in expired:
            await self.session.delete(entry)
        await self.session.commit()
        return len(expired)

    async def delete(self, market_data: CachedMarketData) -> None:
        """Deletes a cached market data entry.

        Args:
            market_data: The CachedMarketData instance to delete.
        """
        await self.session.delete(market_data)
        await self.session.commit()

    async def count(self) -> int:
        """Counts total cached market data entries.

        Returns:
            Total number of entries.
        """
        result = await self.session.execute(
            select(func.count(CachedMarketData.id))
        )
        return result.scalar() or 0

