"""Factory module for creating a fully configured Scheduler.

Keeps FastAPI decoupled from job implementation details.
main.py only calls ``create_scheduler(context)`` and handles start/stop.
"""

from __future__ import annotations

import logging

from app.jobs.base import JobContext
from app.jobs.cleanup_cache import CleanupExpiredCacheJob
from app.jobs.cleanup_old_searches import CleanupOldSearchesJob
from app.jobs.process_search_orders import ProcessSearchOrdersJob
from app.jobs.provider_canary import ProviderCanaryJob
from app.jobs.refresh_market_cache import RefreshMarketCacheJob
from app.jobs.refresh_opportunities import RefreshOpportunityJob
from app.jobs.scheduler import Scheduler
from app.services.job_failure_alert_service import JobFailureAlertService


def create_scheduler(context: JobContext) -> Scheduler:
    """Create and configure a Scheduler with all standard jobs.

    Args:
        context: Shared ``JobContext`` with DB manager and settings.

    Returns:
        A fully configured ``Scheduler`` instance ready to be started.
    """
    scheduler = Scheduler(
        context=context,
        max_concurrent=context.settings.max_concurrent_jobs,
        logger=logging.getLogger("app.jobs.scheduler"),
        job_failure_alert=JobFailureAlertService(),
    )

    # Register all standard jobs with their configured intervals
    scheduler.register(
        RefreshMarketCacheJob(),
        interval=context.settings.cache_refresh_interval,
    )
    scheduler.register(
        RefreshOpportunityJob(),
        interval=context.settings.cache_refresh_interval,
    )
    scheduler.register(
        CleanupExpiredCacheJob(),
        interval=context.settings.cache_refresh_interval,
    )
    # Cleanup de historial: correr a diario; el TTL se usa solo como cutoff de edad
    scheduler.register(
        CleanupOldSearchesJob(),
        interval=86400,  # 24 horas
    )

    # Órdenes de búsqueda en background (PERSONAL.NOAUTH). interval=0 desactiva.
    search_order_interval = int(
        getattr(context.settings, "search_order_interval", 60) or 0
    )
    if search_order_interval > 0:
        scheduler.register(ProcessSearchOrdersJob(), interval=search_order_interval)

    # Canary de scrapers (AS24 0 listings = fail). interval=0 desactiva.
    canary_interval = int(getattr(context.settings, "provider_canary_interval", 21600) or 0)
    if canary_interval > 0:
        scheduler.register(ProviderCanaryJob(), interval=canary_interval)

    return scheduler
