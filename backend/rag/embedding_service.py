"""Generate embeddings using OpenAI."""

import sys
from pathlib import Path
from typing import Optional

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from backend.ai.llm_service import LLMService


class EmbeddingService:
    """OpenAI-based embedding service."""

    def __init__(self, llm: Optional[LLMService] = None):
        self._llm = llm or LLMService()

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return embeddings for a list of texts."""
        return self._llm.embed(texts)
