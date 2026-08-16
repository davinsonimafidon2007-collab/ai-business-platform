"""CleanupOldSearchesJob — Removes search history records older than TTL.

Delegates to ``SearchHistoryRepository.delete_older_than()`` to
periodically purge stale search history data based on the configured
``SEARCH_HISTORY_TTL``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.jobs.base import Job, JobContext, JobResult


class CleanupOldSearchesJob(Job):
    """Periodic job that deletes old search history records.

    Uses the configured ``search_history_ttl`` from settings to
    determine the cutoff age.
    """

    @property
    def name(self) -> str:
        return "cleanup_old_searches"

    async def execute(self, context: JobContext) -> JobResult:
        """Delete search history records older than the configured TTL.

        Args:
            context: JobContext with db_manager and settings.

        Returns:
            JobResult with count of deleted records.
        """
        logger = context.logger
        logger.info("Starting old search history cleanup...")

        try:
            cutoff = datetime.now(UTC) - timedelta(
                seconds=context.settings.search_history_ttl
            )

            async with context.db_manager.get_session() as session:
                from app.repositories.search_history_repository import (
                    SearchHistoryRepository,
                )

                repo = SearchHistoryRepository(session)
                deleted = await repo.delete_older_than(cutoff)

                logger.info(
                    "Old search history cleanup complete. "
                    "Deleted: %d records older than %s",
                    deleted,
                    cutoff.isoformat(),
                )

                return JobResult(
                    success=True,
                    message=f"Deleted {deleted} search history records "
                    f"older than {cutoff.date().isoformat()}",
                    data={
                        "deleted_count": deleted,
                        "cutoff": cutoff.isoformat(),
                    },
                )

        except Exception as exc:
            logger.exception(
                "Old search history cleanup failed: %s", exc
            )
            return JobResult(
                success=False,
                message=f"Old search history cleanup failed: {exc}",
            )

