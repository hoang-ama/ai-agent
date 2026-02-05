"""Weekly scheduled tasks: book summary Monday 9 AM, tech news Tuesday 9 AM."""

import logging
import sys
from pathlib import Path
from typing import Any, Optional

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


def _deliver_if_configured(subject: str, body: str) -> None:
    """If NOTIFICATION_EMAIL is set, send email."""
    try:
        from config.settings import get_settings
        email = get_settings().notification_email
        if not email:
            return
        from backend.tasks.email_handler import compose_gmail
        compose_gmail(to=email, subject=subject, body=body)
    except Exception as e:
        logger.warning("Could not deliver notification: %s", e)


def job_weekly_book_summary() -> None:
    """Scheduled job: summarize a business/self-help book every Monday 9 AM."""
    logger.info("Running weekly book summary job (Monday 9 AM)")
    # Placeholder: use LLM to generate summary of a well-known book or fetch from API
    try:
        from backend.ai.llm_service import LLMService
        llm = LLMService()
        prompt = """Provide a one-paragraph summary and 3–5 key takeaways from one of these books (pick one): 
"Atomic Habits" by James Clear, "Deep Work" by Cal Newport, or "The 7 Habits of Highly Effective People" by Stephen Covey.
Format: Title, Summary, then "Key takeaways:" with bullet points."""
        msgs = [{"role": "user", "content": prompt}]
        out = llm.chat(msgs)
        text = out.get("content", "Summary unavailable.")
        logger.info("Book summary:\n%s", text)
        _deliver_if_configured("Weekly Book Summary & Key Takeaways", text)
    except Exception as e:
        logger.exception("Book summary job failed: %s", e)


def job_weekly_tech_news() -> None:
    """Scheduled job: 10+ tech/AI news updates every Tuesday 9 AM. Uses news handler."""
    logger.info("Running weekly tech news job (Tuesday 9 AM)")
    try:
        from backend.tasks.news_handler import fetch_tech_news_digest
        text = fetch_tech_news_digest()
        if text:
            logger.info("Tech news digest length: %d", len(text))
            _deliver_if_configured("Tech News: AI Agents, Trends & Startups", text)
        else:
            logger.warning("Tech news digest empty")
    except Exception as e:
        logger.exception("Tech news job failed: %s", e)


def register_weekly_jobs() -> None:
    """Register Monday book summary and Tuesday tech news with the scheduler."""
    from backend.scheduler.scheduler import add_cron_job
    add_cron_job("weekly_book_summary", job_weekly_book_summary, CronTrigger(day_of_week="mon", hour=9, minute=0))
    add_cron_job("weekly_tech_news", job_weekly_tech_news, CronTrigger(day_of_week="tue", hour=9, minute=0))
