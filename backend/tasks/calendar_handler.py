"""Google Calendar API integration for adding events."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import sys
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from config.settings import get_settings
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar.events", "https://www.googleapis.com/auth/calendar"]
TOKEN_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "token_calendar.json"


def _get_credentials() -> Optional[Credentials]:
    """Load or refresh Google Calendar OAuth credentials."""
    settings = get_settings()
    creds = None
    if TOKEN_PATH.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        except Exception as e:
            logger.warning("Failed to load token: %s", e)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        if not creds and settings.credentials_path.exists():
            flow = InstalledAppFlow.from_client_secrets_file(
                str(settings.credentials_path), SCOPES
            )
            creds = flow.run_local_server(port=0)
        if creds:
            with open(TOKEN_PATH, "w") as f:
                f.write(creds.to_json())
    return creds


def _parse_datetime(s: str) -> Optional[datetime]:
    """Parse ISO or common datetime string to datetime. Returns UTC naive for API."""
    try:
        from dateutil import parser as date_parser
        dt = date_parser.parse(s)
        if dt.tzinfo:
            dt = dt.astimezone(__import__("datetime").timezone.utc).replace(tzinfo=None)
        return dt
    except Exception:
        return None


def add_calendar_event(
    title: str,
    start_time: str,
    end_time: str,
    description: Optional[str] = None,
) -> dict[str, Any]:
    """
    Add an event to the user's primary Google Calendar.
    start_time and end_time can be ISO 8601 or natural language (e.g. "tomorrow at 3pm").
    """
    creds = _get_credentials()
    if not creds:
        return {"success": False, "error": "Google Calendar not authorized. Please complete OAuth flow."}
    start_dt = _parse_datetime(start_time)
    end_dt = _parse_datetime(end_time)
    if not start_dt or not end_dt:
        return {"success": False, "error": "Could not parse start_time or end_time. Use ISO format or clear natural language."}
    body = {
        "summary": title,
        "description": description or "",
        "start": {"dateTime": start_dt.strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": "UTC"},
        "end": {"dateTime": end_dt.strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": "UTC"},
    }
    try:
        service = build("calendar", "v3", credentials=creds)
        event = service.events().insert(calendarId="primary", body=body).execute()
        return {"success": True, "event_id": event.get("id"), "html_link": event.get("htmlLink")}
    except HttpError as e:
        logger.exception("Calendar API error: %s", e)
        return {"success": False, "error": str(e)}
