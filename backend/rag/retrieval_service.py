"""Semantic search and context retrieval for RAG."""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Optional

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from backend.rag.embedding_service import EmbeddingService
from backend.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


class RetrievalService:
    """Retrieve relevant document chunks by query embedding."""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        embedding_service: Optional[EmbeddingService] = None,
    ):
        self._store = vector_store or VectorStore()
        self._embedding = embedding_service or EmbeddingService()

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Return top_k relevant chunks with metadata."""
        if self._store.count() == 0:
            return []
        embeddings = self._embedding.embed([query])
        results = self._store.query(query_embeddings=embeddings, n_results=top_k)
        docs = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        ids = results.get("ids", [[]])[0]
        out = []
        for i, (doc, meta, id_) in enumerate(zip(docs, metadatas or [{}] * len(docs), ids or [""] * len(docs))):
            out.append({"id": id_, "content": doc, "metadata": meta or {}})
        return out

    def search_json(self, query: str, top_k: int = 5) -> str:
        """Return search results as JSON string for LLM consumption."""
        hits = self.search(query, top_k=top_k)
        return json.dumps({"results": [{"content": h["content"], "source": h["metadata"].get("source", "")} for h in hits]})
