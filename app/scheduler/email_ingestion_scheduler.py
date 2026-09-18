"""Optional scheduler started and stopped by FastAPI's lifespan."""
import logging
from app.config import config
from app.database.db import SessionLocal
from app.services.email_ingestion_service import EmailIngestionService

logger = logging.getLogger(__name__)


def ingest_emails_job():
    with SessionLocal() as db:
        try:
            EmailIngestionService(db).ingest_emails()
        except Exception as exc:
            logger.warning('Gmail sync failed (%s). See protected tracking status.', type(exc).__name__)


def start_scheduler():
    if not (config.GMAIL_ENABLED and config.GMAIL_SCHEDULER_ENABLED):
        return None
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(ingest_emails_job, 'interval', minutes=config.GMAIL_INGESTION_INTERVAL_MINUTES,
                      id='gmail_ingestion', max_instances=1, coalesce=True)
    scheduler.start()
    return scheduler
