"""Intent classification and task routing using LLM and function registry."""

import json
import logging
from typing import Any, Optional

import sys
from pathlib import Path
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from backend.ai.function_registry import FunctionRegistry
from backend.ai.llm_service import LLMService

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a helpful AI assistant. You can:
- Add meetings to Google Calendar
- Create new Apple notes
- Compose new Gmail emails
- Search the user's documents for answers
- Answer general questions

When the user asks you to do something that requires a tool (calendar, note, email, document search), use the appropriate function. Otherwise respond in natural language. Be concise and helpful."""


class TaskRouter:
    """Routes user messages to LLM with tools and executes function calls."""

    def __init__(
        self,
        llm: Optional[LLMService] = None,
        registry: Optional[FunctionRegistry] = None,
    ):
        self.llm = llm or LLMService()
        self.registry = registry or FunctionRegistry()
        self._tools = self.registry.get_tools()

    def process(
        self,
        user_message: str,
        history: Optional[list[dict[str, Any]]] = None,
        image_url_or_base64: Optional[str] = None,
    ) -> str:
        """
        Process user message: build messages, call LLM with tools, execute any
        tool_calls, and return final assistant text. Optionally include image for vision.
        """
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]
        if history:
            messages.extend(history)
        # Build user message content
        content: Any = [{"type": "text", "text": user_message}]
        if image_url_or_base64:
            if image_url_or_base64.startswith("http"):
                content.append({"type": "image_url", "image_url": {"url": image_url_or_base64}})
            else:
                content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_url_or_base64}"}})
        if len(content) == 1:
            content = user_message
        messages.append({"role": "user", "content": content})

        current = list(messages)
        max_rounds = 5
        for _ in range(max_rounds):
            response = self.llm.chat(current, tools=self._tools)
            assistant_content = response.get("content") or ""
            tool_calls = response.get("tool_calls")
            current.append(
                {
                    "role": "assistant",
                    "content": assistant_content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments or "{}"},
                        }
                        for tc in (tool_calls or [])
                    ],
                }
            )
            if not tool_calls:
                return assistant_content
            for tc in tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = self.registry.execute(name, args)
                current.append(
                    {"role": "tool", "tool_call_id": tc.id, "content": result}
                )
        return current[-1].get("content", "") if current else ""
