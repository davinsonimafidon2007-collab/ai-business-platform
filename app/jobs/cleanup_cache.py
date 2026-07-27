"""CleanupExpiredCacheJob — Removes expired market cache entries.

A lightweight job that delegates directly to
``CachedMarketRepository.delete_expired()`` to periodically purge
stale market estimation data.
"""

from __future__ import annotations

from app.jobs.base import Job, JobContext, JobResult


class CleanupExpiredCacheJob(Job):
    """Simple periodic job that deletes expired cache entries.

    The actual deletion logic lives in
    ``CachedMarketRepository.delete_expired()`` — this job merely
    calls it at the configured interval.
    """

    @property
    def name(self) -> str:
        return "cleanup_expired_cache"

    async def execute(self, context: JobContext) -> JobResult:
        """Delete all expired cached market data entries.

        Args:
            context: JobContext with db_manager and settings.

        Returns:
            JobResult with count of deleted entries.
        """
        logger = context.logger
        logger.info("Starting expired cache cleanup...")

        try:
            async with context.db_manager.get_session() as session:
                from app.repositories.cached_market_repository import (
                    CachedMarketRepository,
                )

                repo = CachedMarketRepository(session)
                deleted = await repo.delete_expired()

                logger.info(
                    "Expired cache cleanup complete. Deleted: %d",
                    deleted,
                )

                return JobResult(
                    success=True,
                    message=f"Deleted {deleted} expired cache entries",
                    data={"deleted_count": deleted},
                )

        except Exception as exc:
            logger.exception("Expired cache cleanup failed: %s", exc)
            return JobResult(
                success=False,
                message=f"Expired cache cleanup failed: {exc}",
            )

