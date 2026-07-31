"""APScheduler lifecycle.

The scheduler object exists now so the application lifespan has something to
start and stop. No jobs are registered yet — the periodic metadata scan is
added here once the DataHub integration lands.
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")


def start_scheduler() -> None:
    """Start background jobs when ``SCHEDULER_ENABLED`` is set."""
    if not settings.scheduler_enabled:
        logger.info("Scheduler disabled (SCHEDULER_ENABLED=false)")
        return

    if scheduler.running:
        return

    # register_jobs(scheduler) — added with the scan implementation.
    scheduler.start()
    logger.info(
        "Scheduler started (scan interval: %s minutes)",
        settings.scan_interval_minutes,
    )


def shutdown_scheduler() -> None:
    """Stop background jobs without waiting for in-flight runs to finish."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
