"""Document ingestion: process files and add to vector store for RAG."""

import logging
import re
import sys
from pathlib import Path
from typing import Any, Optional, Union, Dict

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from backend.rag.document_processor import process_document
from backend.rag.embedding_service import EmbeddingService
from backend.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


def _safe_doc_id(name: str) -> str:
    """ASCII-safe id for ChromaDB (avoids encoding issues with unicode filenames)."""
    stem = Path(name).stem
    safe = re.sub(r"[^\w\-]", "_", stem)[:80] or "doc"
    return safe.encode("ascii", "replace").decode("ascii")


def ingest_document(
    path: Union[str, Path],
    doc_id: Optional[str] = None,
    original_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Load document, chunk, embed, and add to vector store. Returns counts."""
    path = Path(path)
    if not path.exists():
        return {"success": False, "error": f"File not found: {path}"}
    base_id = doc_id or _safe_doc_id(original_name or path.name)
    store = VectorStore()
    embed_svc = EmbeddingService()
    chunks = []
    metas = []
    for chunk_text, meta in process_document(path, doc_id=base_id):
        chunks.append(chunk_text)
        metas.append(meta)
    if not chunks:
        return {"success": False, "error": "No text extracted from document"}
    try:
        embeddings = embed_svc.embed(chunks)
    except Exception as e:
        logger.exception("Embedding failed: %s", e)
        return {"success": False, "error": f"Embedding failed: {e}. Check OPENAI_API_KEY and quota."}
    try:
        ids = [f"{base_id}_{i}" for i in range(len(chunks))]
        store.add(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metas)
    except Exception as e:
        logger.exception("Vector store add failed: %s", e)
        return {"success": False, "error": str(e)}
    return {"success": True, "chunks": len(chunks), "source": original_name or path.name}
