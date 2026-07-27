"""Job Scheduling System.

Provides a reusable async scheduler and self-contained job implementations
for background maintenance tasks like cache refreshes, opportunity
recalculation, and data cleanup.

Usage:
    from app.jobs.factory import create_scheduler
    from app.jobs.base import JobContext

    context = JobContext(db_manager=..., settings=..., logger=...)
    scheduler = create_scheduler(context)
    await scheduler.start()
    # ... later ...
    await scheduler.stop()
"""

from app.jobs.base import Job, JobContext, JobMetrics, JobResult, JobStatus

__all__ = [
    "Job",
    "JobContext",
    "JobMetrics",
    "JobResult",
    "JobStatus",
]

