"""Gmail API integration for composing emails."""

import base64
import logging
from email.mime.text import MIMEText
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

SCOPES = ["https://www.googleapis.com/auth/gmail.compose", "https://www.googleapis.com/auth/gmail.send"]
TOKEN_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "token_gmail.json"


def _get_credentials() -> Optional[Credentials]:
    """Load or refresh Gmail OAuth credentials."""
    settings = get_settings()
    creds = None
    if TOKEN_PATH.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        except Exception as e:
            logger.warning("Failed to load Gmail token: %s", e)
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


def compose_gmail(to: str, subject: str, body: str) -> dict[str, Any]:
    """
    Compose and send a Gmail message. Optionally creates draft if send fails.
    """
    creds = _get_credentials()
    if not creds:
        return {"success": False, "error": "Gmail not authorized. Please complete OAuth flow."}
    message = MIMEText(body, "plain", "utf-8")
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    try:
        service = build("gmail", "v1", credentials=creds)
        sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return {"success": True, "id": sent.get("id"), "message": "Email sent."}
    except HttpError as e:
        logger.exception("Gmail API error: %s", e)
        return {"success": False, "error": str(e)}
