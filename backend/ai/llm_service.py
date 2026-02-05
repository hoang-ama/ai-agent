"""OpenAI API wrapper with function calling support."""

import logging
from typing import Any, Optional

from openai import OpenAI

import sys
from pathlib import Path
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
from config.settings import get_settings

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-5-mini"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


class LLMService:
    """OpenAI LLM service with chat and function calling."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    ):
        settings = get_settings()
        self._client = OpenAI(api_key=api_key or settings.openai_api_key)
        self.model = model
        self.embedding_model = embedding_model

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        tool_choice: Optional[str] = "auto",
    ) -> dict[str, Any]:
        """
        Send chat completion request. If tools are provided, supports function calling.
        Returns the assistant message and optional tool_calls.
        """
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice
        try:
            response = self._client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            out = {
                "content": getattr(choice.message, "content", None) or "",
                "role": choice.message.role,
                "tool_calls": getattr(choice.message, "tool_calls", None),
            }
            return out
        except Exception as e:
            logger.exception("OpenAI chat error: %s", e)
            raise

    def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        max_rounds: int = 5,
    ) -> tuple[str, list[dict[str, Any]]]:
        """
        Run chat with function calling: execute tools and append results until
        the model returns a final text response or max_rounds is reached.
        Returns (final_text_response, updated_messages).
        """
        current = list(messages)
        for _ in range(max_rounds):
            response = self.chat(current, tools=tools)
            current.append(
                {
                    "role": "assistant",
                    "content": response.get("content") or "",
                    "tool_calls": response.get("tool_calls"),
                }
            )
            tool_calls = response.get("tool_calls")
            if not tool_calls:
                return (response.get("content") or "", current)
            for tc in tool_calls:
                tid = tc.id
                name = tc.function.name
                args_str = tc.function.arguments or "{}"
                try:
                    import json
                    args = json.loads(args_str)
                except json.JSONDecodeError:
                    args = {}
                # Caller must inject tool execution; we only append placeholder
                # so the registry can be used by the caller to run and fill in.
                current.append(
                    {
                        "role": "tool",
                        "tool_call_id": tid,
                        "content": f"[Tool {name} called with args; result to be injected by caller]",
                    }
                )
        return (current[-1].get("content", ""), current)

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return embeddings for a list of texts."""
        if not texts:
            return []
        try:
            r = self._client.embeddings.create(
                model=self.embedding_model,
                input=texts,
            )
            return [item.embedding for item in r.data]
        except Exception as e:
            logger.exception("OpenAI embed error: %s", e)
            raise

    def transcribe_audio(self, file_path: str) -> str:
        """Transcribe audio file using Whisper."""
        with open(file_path, "rb") as f:
            response = self._client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
            )
        return response.text
