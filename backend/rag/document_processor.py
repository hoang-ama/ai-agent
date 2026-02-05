"""Parse PDF, TXT, MD, DOCX into text chunks."""

import logging
from pathlib import Path
from typing import Any, Generator

logger = logging.getLogger(__name__)

CHUNK_SIZE = 800
CHUNK_OVERLAP = 200


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks."""
    if not text or not text.strip():
        return []
    chunks = []
    start = 0
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    while start < len(text):
        end = start + chunk_size
        if end >= len(text):
            chunks.append(text[start:].strip())
            break
        # Try to break at paragraph or sentence
        break_at = text.rfind("\n\n", start, end + 1)
        if break_at == -1:
            break_at = text.rfind("\n", start, end + 1)
        if break_at == -1:
            break_at = text.rfind(". ", start, end + 1)
        if break_at != -1 and break_at > start:
            end = break_at + 1
        chunks.append(text[start:end].strip())
        start = end - overlap if overlap < end else end
    return [c for c in chunks if c]


def extract_text_from_pdf(path: Path) -> str:
    """Extract text from PDF using pypdf."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        logger.warning("PDF extract failed for %s: %s", path, e)
        return ""


def extract_text_from_docx(path: Path) -> str:
    """Extract text from DOCX using python-docx."""
    try:
        from docx import Document
        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception as e:
        logger.warning("DOCX extract failed for %s: %s", path, e)
        return ""


def extract_text_from_file(path: Path) -> str:
    """Dispatch by extension: PDF, DOCX, TXT, MD."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(path)
    if suffix == ".docx":
        return extract_text_from_docx(path)
    if suffix in (".txt", ".md", ".markdown"):
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.warning("Text read failed for %s: %s", path, e)
            return ""
    logger.warning("Unsupported format: %s", suffix)
    return ""


def process_document(
    path: Path,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    doc_id: str = "",
) -> Generator[tuple[str, dict[str, Any]], None, None]:
    """
    Read document and yield (chunk_text, metadata) for each chunk.
    doc_id is used as prefix for chunk ids.
    """
    path = Path(path)
    text = extract_text_from_file(path)
    if not text:
        return
    chunks = _chunk_text(text, chunk_size=chunk_size, overlap=chunk_overlap)
    base_id = doc_id or path.stem
    for i, chunk in enumerate(chunks):
        meta = {"source": str(path.name), "chunk_index": i}
        yield chunk, meta
