"""FastAPI application with health check and WebSocket support."""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Import settings from config (path relative to project root)
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from config.settings import get_settings
from backend.services import get_task_router
from backend.scheduler.scheduler import start_scheduler, stop_scheduler
from backend.scheduler.daily_tasks import register_daily_jobs
from backend.scheduler.weekly_tasks import register_weekly_jobs

logging.basicConfig(
    level=getattr(logging, get_settings().log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("Starting AI Agent backend")
    register_daily_jobs()
    register_weekly_jobs()
    start_scheduler()
    yield
    stop_scheduler()
    logger.info("Shutting down AI Agent backend")


app = FastAPI(
    title="AI Agent API",
    description="Backend API for AI Assistant chatbot",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Return consistent JSON error for unhandled exceptions."""
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc) if get_settings().is_development() else None},
    )


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint for liveness/readiness probes."""
    return {"status": "ok", "service": "ai-agent-backend"}


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "AI Agent API", "docs": "/docs"}


class ChatRequest(BaseModel):
    message: str
    history: Optional[list[dict[str, str]]] = None
    image_base64: Optional[str] = None


class ChatResponse(BaseModel):
    response: str


def _safe_filename(original: str) -> str:
    """Return a filesystem-safe name: keep extension, use ASCII stem + timestamp to avoid encoding/collision issues."""
    import re
    import time
    p = Path(original or "upload")
    ext = p.suffix.lower()
    safe_stem = re.sub(r"[^\w\-.]", "_", p.stem)[:80] or "doc"
    safe_stem = safe_stem.encode("ascii", "replace").decode("ascii")
    return f"{safe_stem}_{int(time.time())}{ext}"


@app.post("/ingest")
async def ingest_doc(file: UploadFile = File(...)) -> dict[str, Any]:
    """Upload a document (PDF, TXT, MD, DOCX) for RAG learning."""
    allowed = {".pdf", ".txt", ".md", ".docx"}
    if file.filename:
        ext = Path(file.filename).suffix.lower()
        if ext not in allowed:
            raise HTTPException(400, detail=f"Unsupported format. Allowed: {allowed}")
    try:
        from backend.tasks.document_handler import ingest_document
        settings = get_settings()
        settings.documents_dir.mkdir(parents=True, exist_ok=True)
        safe_name = _safe_filename(file.filename or "upload")
        path = settings.documents_dir / safe_name
        content = await file.read()
        path.write_bytes(content)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: ingest_document(path, original_name=file.filename))
        if not result.get("success"):
            raise HTTPException(422, detail=result.get("error", "Ingest failed"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Ingest failed: %s", e)
        detail = "Document ingestion failed"
        if get_settings().is_development():
            detail = str(e)
        raise HTTPException(500, detail=detail)


@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)) -> dict[str, Any]:
    """Transcribe audio file using Whisper. Returns {"text": "..."}."""
    import os
    import tempfile
    if not file.filename:
        raise HTTPException(400, detail="Missing filename")
    try:
        from backend.ai.llm_service import LLMService
        content = await file.read()
        if not content:
            raise HTTPException(400, detail="Empty file")
        suffix = Path(file.filename).suffix.lower() or ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            llm = LLMService()
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(None, lambda: llm.transcribe_audio(tmp_path))
            return {"text": text or ""}
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Transcribe failed: %s", e)
        raise HTTPException(500, detail="Transcription failed")


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Process user message with LLM and tools; return assistant response."""
    if not (request.message or request.message.strip()):
        raise HTTPException(400, detail="Message cannot be empty")
    settings = get_settings()
    if not (settings.openai_api_key or settings.openai_api_key.strip()):
        raise HTTPException(
            503,
            detail="OPENAI_API_KEY is not set. Add it to your .env file and restart the backend.",
        )
    try:
        router = get_task_router()
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: router.process(
                request.message,
                history=request.history,
                image_url_or_base64=request.image_base64,
            ),
        )
        return ChatResponse(response=response or "")
    except Exception as e:
        logger.exception("Chat failed: %s", e)
        detail = "Assistant request failed. Please try again."
        if settings.is_development():
            detail = str(e)
        raise HTTPException(500, detail=detail)


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for real-time chat."""
    await websocket.accept()
    logger.info("WebSocket client connected")
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data) if data else {}
            # Echo back for now; will be wired to LLM and task handlers later
            response = {"type": "message", "content": f"Received: {payload.get('message', data)}"}
            await websocket.send_json(response)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except json.JSONDecodeError:
        await websocket.send_json({"type": "error", "content": "Invalid JSON"})
    except Exception as e:
        logger.exception("WebSocket error: %s", e)
        try:
            await websocket.send_json({"type": "error", "content": str(e)})
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "backend.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.is_development(),
    )
