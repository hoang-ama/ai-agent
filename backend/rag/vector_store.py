"""ChromaDB vector store for document embeddings."""

import logging
import sys
from pathlib import Path
from typing import Any, Optional

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from config.settings import get_settings
import chromadb
from chromadb.config import Settings as ChromaSettings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "documents"


class VectorStore:
    """ChromaDB-backed vector store for document chunks."""

    def __init__(self, persist_directory: Optional[str] = None, collection_name: str = COLLECTION_NAME):
        settings = get_settings()
        path = persist_directory or str(settings.embeddings_dir)
        self._client = chromadb.PersistentClient(
            path=path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection_name = collection_name
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Document chunks for RAG"},
        )

    def add(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: Optional[list[dict[str, Any]]] = None,
    ) -> None:
        """Add document chunks with embeddings."""
        kwargs: dict[str, Any] = {
            "ids": ids,
            "embeddings": embeddings,
            "documents": documents,
        }
        if metadatas is not None:
            kwargs["metadatas"] = metadatas
        self._collection.add(**kwargs)
        logger.info("Added %d chunks to vector store", len(ids))

    def query(
        self,
        query_embeddings: list[list[float]],
        n_results: int = 5,
        where: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Query by embedding; returns ids, documents, metadatas, distances."""
        return self._collection.query(
            query_embeddings=query_embeddings,
            n_results=n_results,
            where=where,
        )

    def delete(self, ids: Optional[list[str]] = None, where: Optional[dict[str, Any]] = None) -> None:
        """Delete by ids or where filter."""
        self._collection.delete(ids=ids, where=where)

    def count(self) -> int:
        """Return number of items in collection."""
        return self._collection.count()
