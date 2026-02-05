"""Social media and news aggregation for tech/AI updates."""

import logging
import sys
from pathlib import Path
from typing import Any, Optional

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from config.settings import get_settings

logger = logging.getLogger(__name__)


def _fetch_reddit_tech() -> list[dict[str, Any]]:
    """Fetch tech/AI posts from Reddit (r/artificial, r/MachineLearning, etc.)."""
    try:
        import praw
        settings = get_settings()
        if not settings.reddit_client_id or not settings.reddit_client_secret:
            return []
        reddit = praw.Reddit(
            client_id=settings.reddit_client_id,
            client_secret=settings.reddit_client_secret,
            user_agent=settings.reddit_user_agent or "AI-Agent/1.0",
        )
        items = []
        for sub in ["artificial", "MachineLearning", "artificialintelligence", "startups"]:
            try:
                subreddit = reddit.subreddit(sub)
                for post in subreddit.hot(limit=5):
                    items.append({
                        "title": post.title,
                        "url": f"https://reddit.com{post.permalink}",
                        "source": f"r/{sub}",
                        "score": post.score,
                    })
            except Exception as e:
                logger.warning("Reddit sub %s: %s", sub, e)
        return items[:20]
    except Exception as e:
        logger.warning("Reddit fetch failed: %s", e)
        return []


def _fetch_twitter_tech() -> list[dict[str, Any]]:
    """Fetch tech/AI tweets if Twitter bearer token is set."""
    try:
        import tweepy
        settings = get_settings()
        if not settings.twitter_bearer_token:
            return []
        client = tweepy.Client(bearer_token=settings.twitter_bearer_token)
        # Search recent tweets about AI agents, AI trends
        query = "AI agents OR AI transformation OR AI trends OR AI startups -is:retweet lang:en"
        response = client.search_recent_tweets(
            query=query,
            max_results=20,
            tweet_fields=["created_at", "text"],
        )
        if not response.data:
            return []
        return [
            {"title": t.text[:100] + "..." if len(t.text) > 100 else t.text, "url": "", "source": "Twitter"}
            for t in response.data
        ]
    except Exception as e:
        logger.warning("Twitter fetch failed: %s", e)
        return []


def _format_digest(items: list[dict[str, Any]], min_count: int = 10) -> str:
    """Format items as a text digest. Pad with placeholder if fewer than min_count."""
    lines = []
    for i, item in enumerate(items[:min_count], 1):
        title = item.get("title", "")
        url = item.get("url", "")
        source = item.get("source", "")
        line = f"{i}. {title}"
        if url:
            line += f"\n   {url}"
        if source:
            line += f" (Source: {source})"
        lines.append(line)
    while len(lines) < min_count:
        lines.append(f"{len(lines)+1}. [Placeholder: Add more sources or APIs for additional updates.]")
    return "Tech News: AI Agents, AI Transformation, AI Trends & Startups\n\n" + "\n\n".join(lines)


def fetch_tech_news_digest(min_items: int = 10) -> str:
    """Fetch at least min_items tech/AI updates from Reddit (and optionally Twitter) and return formatted digest."""
    items = _fetch_reddit_tech() + _fetch_twitter_tech()
    # Dedupe by title
    seen = set()
    unique = []
    for x in items:
        t = (x.get("title") or "").strip()
        if t and t not in seen:
            seen.add(t)
            unique.append(x)
    return _format_digest(unique, min_count=min_items)
