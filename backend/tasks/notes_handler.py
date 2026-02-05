"""Apple Notes creation via AppleScript (macOS)."""

import logging
import platform
import subprocess
from typing import Any, Optional

logger = logging.getLogger(__name__)


def create_apple_note(title: str, body: str) -> dict[str, Any]:
    """
    Create a new note in Apple Notes. macOS only; uses AppleScript.
    """
    if platform.system() != "Darwin":
        return {"success": False, "error": "Apple Notes is only available on macOS."}
    # Escape backslashes and quotes for AppleScript string; newlines -> space to keep one-line script
    def escape(s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("\r", " ")
    title_esc = escape(title)
    body_esc = escape(body)
    script = f'''
    tell application "Notes"
        make new note at folder "Notes" with properties {{name: "{title_esc}", body: "{body_esc}"}}
    end tell
    '''
    try:
        subprocess.run(
            ["osascript", "-e", script],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return {"success": True, "message": f"Note '{title}' created."}
    except subprocess.CalledProcessError as e:
        logger.exception("AppleScript Notes error: %s", e)
        return {"success": False, "error": e.stderr or str(e)}
    except FileNotFoundError:
        return {"success": False, "error": "osascript not found (non-macOS?)."}
    except Exception as e:
        logger.exception("create_apple_note error: %s", e)
        return {"success": False, "error": str(e)}
