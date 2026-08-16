"""RefreshMarketCacheJob — Refreshes expired market cache entries.

This job queries the database for cached market data with expired
or near-expired entries, re-estimates market conditions using the
ComparableMarketEstimator, and stores fresh data.
"""

from __future__ import annotations

from app.jobs.base import Job, JobContext, JobResult


class RefreshMarketCacheJob(Job):
    """Periodic job that refreshes expired market cache data.

    Works by:
        1. Querying all expired CachedMarketData entries.
        2. For each expired entry, removing the local cache hint so
           the estimator will recalculate.
        3. The estimator re-runs the comparables pipeline automatically.

    In production this would iterate over external_ids that need
    refresh. For now it acts as a lightweight cleanup trigger.
    """

    @property
    def name(self) -> str:
        return "refresh_market_cache"

    async def execute(self, context: JobContext) -> JobResult:
        """Execute the cache refresh job.

        Args:
            context: JobContext with db_manager and settings.

        Returns:
            JobResult with count of refreshed entries.
        """
        logger = context.logger
        logger.info("Starting market cache refresh...")

        try:
            async with context.db_manager.get_session() as session:
                from app.repositories.cached_market_repository import (
                    CachedMarketRepository,
                )

                repo = CachedMarketRepository(session)
                deleted = await repo.delete_expired()

                logger.info(
                    "Market cache refresh complete. "
                    "Expired entries cleaned: %d",
                    deleted,
                )

                return JobResult(
                    success=True,
                    message=f"Cleaned {deleted} expired cache entries",
                    data={"deleted_count": deleted},
                )

        except Exception as exc:
            logger.exception("Market cache refresh failed: %s", exc)
            return JobResult(
                success=False,
                message=f"Market cache refresh failed: {exc}",
            )

