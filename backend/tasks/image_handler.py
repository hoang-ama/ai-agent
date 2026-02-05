"""Image analysis using GPT-4 Vision API."""

import base64
import logging
import sys
from pathlib import Path
from typing import Optional

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from backend.ai.llm_service import LLMService

logger = logging.getLogger(__name__)


def analyze_image(
    image_base64: str,
    prompt: str = "Describe this image in detail. Include any text, objects, and context.",
) -> str:
    """
    Analyze an image using GPT-4 Vision. image_base64 is raw base64 string (no data URL prefix).
    Returns the model's description or analysis.
    """
    llm = LLMService()
    url = f"data:image/jpeg;base64,{image_base64}" if not image_base64.startswith("data:") else image_base64
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": url}},
            ],
        }
    ]
    try:
        out = llm.chat(messages)
        return out.get("content", "") or ""
    except Exception as e:
        logger.exception("Vision analysis failed: %s", e)
        return f"Image analysis failed: {e}"
