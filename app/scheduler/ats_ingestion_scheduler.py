"""Background scheduler for daily ATS/job-board collection."""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import config

logger = logging.getLogger(__name__)
_scheduler = None


def _run_collection_job() -> None:
    from app.scheduler.ats_scheduler import acquisition_lock, run_collection

    with acquisition_lock(timeout_secs=5):
        run_collection()


def start_ats_scheduler():
    """Start scheduled offer collection if enabled."""
    global _scheduler
    if not config.ATS_SCHEDULER_ENABLED:
        return None
    if _scheduler:
        return _scheduler

    scheduler = BackgroundScheduler(timezone="Europe/Paris")
    for raw_time in config.ATS_SCHEDULER_TIMES.split(","):
        raw_time = raw_time.strip()
        if not raw_time:
            continue
        hour, minute = [int(part) for part in raw_time.split(":", 1)]
        scheduler.add_job(
            _run_collection_job,
            CronTrigger(hour=hour, minute=minute),
            id=f"ats_collection_{hour:02d}{minute:02d}",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

    if not scheduler.get_jobs():
        logger.warning("ATS scheduler enabled but no valid ATS_SCHEDULER_TIMES configured")
        return None
    scheduler.start()
    _scheduler = scheduler
    logger.info("ATS scheduler started at %s", config.ATS_SCHEDULER_TIMES)
    return scheduler
