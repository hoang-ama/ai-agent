"""Registry of tools/functions available to the LLM."""

import json
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# OpenAI tool schema: list of {"type": "function", "function": {"name", "description", "parameters"}}
OPENAI_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "add_calendar_event",
            "description": "Add a meeting or event to Google Calendar. Use when the user wants to schedule a meeting, add an event, or create a calendar entry.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Title of the event"},
                    "start_time": {"type": "string", "description": "Start time in ISO 8601 or natural format"},
                    "end_time": {"type": "string", "description": "End time in ISO 8601 or natural format"},
                    "description": {"type": "string", "description": "Optional event description"},
                },
                "required": ["title", "start_time", "end_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_apple_note",
            "description": "Create a new note in Apple Notes. Use when the user wants to create a note, save something to Notes, or add an Apple note.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Title of the note"},
                    "body": {"type": "string", "description": "Body content of the note"},
                },
                "required": ["title", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compose_gmail",
            "description": "Compose a new Gmail email. Use when the user wants to send an email, write an email, or compose a Gmail.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Email subject"},
                    "body": {"type": "string", "description": "Email body (plain text or HTML)"},
                },
                "required": ["to", "subject", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": "Search the user's learned documents for relevant information. Use when the user asks a question that might be answered by their uploaded documents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "top_k": {"type": "integer", "description": "Number of results to return", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
]


class FunctionRegistry:
    """Registry that maps tool names to callables and provides OpenAI tool schemas."""

    def __init__(self):
        self._handlers: dict[str, Callable[..., Any]] = {}
        self._tools = OPENAI_TOOLS

    def register(self, name: str, handler: Callable[..., Any]) -> None:
        self._handlers[name] = handler

    def get_tools(self) -> list[dict[str, Any]]:
        return self._tools

    def execute(self, name: str, arguments: dict[str, Any]) -> str:
        """Execute a registered function by name. Returns result as string for LLM."""
        if name not in self._handlers:
            return json.dumps({"error": f"Unknown tool: {name}"})
        try:
            result = self._handlers[name](**arguments)
            if isinstance(result, str):
                return result
            return json.dumps(result) if result is not None else "Done"
        except Exception as e:
            logger.exception("Tool %s failed: %s", name, e)
            return json.dumps({"error": str(e)})

    def get_handler(self, name: str) -> Optional[Callable[..., Any]]:
        return self._handlers.get(name)
