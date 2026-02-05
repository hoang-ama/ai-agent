"""Service wiring: function registry with all handlers and task router."""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from backend.ai.function_registry import FunctionRegistry
from backend.ai.task_router import TaskRouter
from backend.rag.retrieval_service import RetrievalService
from backend.tasks.calendar_handler import add_calendar_event
from backend.tasks.notes_handler import create_apple_note
from backend.tasks.email_handler import compose_gmail


def _search_documents(query: str, top_k: int = 5) -> str:
    """Search learned documents via RAG."""
    svc = RetrievalService()
    return svc.search_json(query, top_k=top_k)


def get_registry() -> FunctionRegistry:
    """Return a FunctionRegistry with calendar, notes, email, and document search registered."""
    reg = FunctionRegistry()
    reg.register("add_calendar_event", add_calendar_event)
    reg.register("create_apple_note", create_apple_note)
    reg.register("compose_gmail", compose_gmail)
    reg.register("search_documents", _search_documents)
    return reg


def get_task_router() -> TaskRouter:
    """Return TaskRouter with LLM and registry wired."""
    return TaskRouter(registry=get_registry())
