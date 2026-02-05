"""APScheduler with timezone support for scheduled tasks."""

import logging
import sys
from pathlib import Path
from typing import Optional

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from config.settings import get_settings

logger = logging.getLogger(__name__)

_scheduler: Optional[BackgroundScheduler] = None


def get_scheduler() -> BackgroundScheduler:
    """Return singleton BackgroundScheduler with app timezone."""
    global _scheduler
    if _scheduler is None:
        settings = get_settings()
        _scheduler = BackgroundScheduler(timezone=settings.timezone)
        logger.info("Scheduler created with timezone=%s", settings.timezone)
    return _scheduler


def start_scheduler() -> None:
    """Start the scheduler (call after adding jobs)."""
    s = get_scheduler()
    if not s.running:
        s.start()
        logger.info("Scheduler started")


def stop_scheduler() -> None:
    """Stop the scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped")


def add_cron_job(job_id: str, func, trigger: CronTrigger, replace_existing: bool = True) -> None:
    """Add a cron job to the scheduler."""
    s = get_scheduler()
    s.add_job(func, trigger=trigger, id=job_id, replace_existing=replace_existing)
    logger.info("Added job %s", job_id)
