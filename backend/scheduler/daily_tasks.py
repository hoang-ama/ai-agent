"""Daily scheduled tasks: 10 words at 8 AM, 5 quotes at 11 AM."""

import json
import logging
import random
import sys
from pathlib import Path
from typing import Any

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

# In-memory fallback; can be replaced with file/API word list
WORDS_SAMPLE = [
    {"word": "ephemeral", "definition": "Lasting for a very short time.", "example": "Fame in the digital age is often ephemeral."},
    {"word": "ubiquitous", "definition": "Present everywhere at the same time.", "example": "Smartphones have become ubiquitous."},
    {"word": "paradigm", "definition": "A typical example or pattern of something.", "example": "This discovery represents a paradigm shift."},
    {"word": "synthesize", "definition": "Combine into a coherent whole.", "example": "She synthesized ideas from multiple sources."},
    {"word": "resilient", "definition": "Able to withstand or recover quickly from difficulties.", "example": "Children are often remarkably resilient."},
    {"word": "pragmatic", "definition": "Dealing with things sensibly and realistically.", "example": "We need a pragmatic approach to the problem."},
    {"word": "nuance", "definition": "A subtle difference in meaning or expression.", "example": "The nuance of his argument was lost in translation."},
    {"word": "catalyst", "definition": "Something that precipitates an event or change.", "example": "The protest was a catalyst for reform."},
    {"word": "mitigate", "definition": "Make less severe, serious, or painful.", "example": "Measures to mitigate climate change."},
    {"word": "leverage", "definition": "Use something to maximum advantage.", "example": "We can leverage our existing network."},
    {"word": "holistic", "definition": "Characterized by the belief that parts are interconnected.", "example": "A holistic approach to health."},
    {"word": "disrupt", "definition": "Interrupt by causing a disturbance.", "example": "Technology continues to disrupt industries."},
    {"word": "iterate", "definition": "Perform or utter repeatedly.", "example": "We iterate on the product based on feedback."},
    {"word": "scalable", "definition": "Able to be scaled or expanded.", "example": "A scalable business model."},
    {"word": "align", "definition": "Place or arrange in a straight line or in correct relative positions.", "example": "Goals must align with company strategy."},
]

QUOTES_SAMPLE = [
    "The only way to do great work is to love what you do. — Steve Jobs",
    "Innovation distinguishes between a leader and a follower. — Steve Jobs",
    "It does not matter how slowly you go as long as you do not stop. — Confucius",
    "The future belongs to those who believe in the beauty of their dreams. — Eleanor Roosevelt",
    "Success is not final, failure is not fatal: it is the courage to continue that counts. — Winston Churchill",
    "The only impossible journey is the one you never begin. — Tony Robbins",
    "Your time is limited, don't waste it living someone else's life. — Steve Jobs",
    "Do what you can, with what you have, where you are. — Theodore Roosevelt",
    "The best time to plant a tree was 20 years ago. The second best time is now. — Chinese Proverb",
    "Believe you can and you're halfway there. — Theodore Roosevelt",
]


def get_ten_words() -> list[dict[str, Any]]:
    """Return 10 random words to learn. Extend with API or file later."""
    pool = list(WORDS_SAMPLE)
    if len(pool) < 10:
        return pool
    return random.sample(pool, 10)


def get_five_quotes() -> list[str]:
    """Return 5 random inspiring quotes."""
    pool = list(QUOTES_SAMPLE)
    if len(pool) < 5:
        return pool
    return random.sample(pool, 5)


def job_daily_words() -> None:
    """Scheduled job: 10 words at 8 AM. Log and optionally send via notification."""
    logger.info("Running daily words job (8 AM)")
    words = get_ten_words()
    text = "10 words to learn today:\n\n" + "\n\n".join(
        f"• {w['word']}: {w['definition']}\n  Example: {w['example']}" for w in words
    )
    logger.info("Daily words:\n%s", text)
    # TODO: send to NOTIFICATION_EMAIL or in-app when notification system is added
    _deliver_if_configured("10 Words to Learn", text)


def job_daily_quotes() -> None:
    """Scheduled job: 5 quotes at 11 AM."""
    logger.info("Running daily quotes job (11 AM)")
    quotes = get_five_quotes()
    text = "5 inspiring quotes for you:\n\n" + "\n\n".join(f"• {q}" for q in quotes)
    logger.info("Daily quotes:\n%s", text)
    _deliver_if_configured("5 Inspiring Quotes", text)


def _deliver_if_configured(subject: str, body: str) -> None:
    """If NOTIFICATION_EMAIL is set, send email (requires Gmail handler)."""
    try:
        from config.settings import get_settings
        email = get_settings().notification_email
        if not email:
            return
        from backend.tasks.email_handler import compose_gmail
        compose_gmail(to=email, subject=subject, body=body)
    except Exception as e:
        logger.warning("Could not deliver notification: %s", e)


def register_daily_jobs() -> None:
    """Register 8 AM words and 11 AM quotes with the scheduler."""
    from backend.scheduler.scheduler import add_cron_job
    add_cron_job("daily_words", job_daily_words, CronTrigger(hour=8, minute=0))
    add_cron_job("daily_quotes", job_daily_quotes, CronTrigger(hour=11, minute=0))
