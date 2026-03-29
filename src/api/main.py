"""Local-only FastAPI surface for the web UI."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
import warnings
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import uvicorn

# Hugging Face Hub prints a harmless stderr warning on cache checks; it does not stop the server.
warnings.filterwarnings(
    "ignore",
    message=".*unauthenticated requests to the HF Hub.*",
    category=UserWarning,
)
from fastapi import Body, Depends, FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse

from src.api.schemas import (
    ChatRequest,
    LlmSettingsOut,
    LlmSettingsPatch,
    SegmentOut,
    SessionOut,
    SessionPatch,
    SummarizeBody,
    meeting_to_session_out,
)
from src.config import DATA_DIR, EMBEDDING_MODEL, FAISS_DIR, LLM_MODEL, WHISPER_MODEL
from src.db.connection import connect
from src.db.llm_settings import (
    get_effective_max_new_tokens,
    get_effective_model_id,
    get_llm_settings_view,
    patch_llm_settings as apply_llm_settings_patch,
)
from src.db.migrations import run_migrations
from src.db.repository import ChatRepo, SegmentRepo
from src.db.schema import init_db
from src.indexing.pipeline import index_session
from src.rag.chat_service import prepare_rag_stream
from src.rag.llm import LLM
from src.services.session_service import SessionService
from src.system.health import health_snapshot

# #region agent log
_AGENT_DEBUG_LOG = Path(__file__).resolve().parent.parent.parent / ".cursor" / "debug-9de7c3.log"


def _agent_debug_ndjson(message: str, data: dict, hypothesis_id: str) -> None:
    try:
        payload = {
            "sessionId": "9de7c3",
            "message": message,
            "data": data,
            "hypothesisId": hypothesis_id,
            "timestamp": int(time.time() * 1000),
        }
        _AGENT_DEBUG_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(_AGENT_DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception:
        pass


# #endregion


@asynccontextmanager
async def lifespan(app: FastAPI):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    FAISS_DIR.mkdir(parents=True, exist_ok=True)
    conn = connect(check_same_thread=False)
    init_db(conn)
    run_migrations(conn)
    app.state.conn = conn
    app.state.db_lock = threading.Lock()
    # #region agent log
    paths = []
    for r in app.routes:
        p = getattr(r, "path", None)
        if isinstance(p, str):
            paths.append(p)
    settings_paths = [p for p in paths if "settings" in p]
    _agent_debug_ndjson(
        "lifespan_startup_routes",
        {
            "route_count": len(paths),
            "has_api_settings_llm_get": "/api/settings/llm" in paths,
            "settings_related_paths": settings_paths,
            "pid": os.getpid(),
        },
        "H1-H3",
    )
    # #endregion
    yield
    conn.close()


app = FastAPI(title="Local Meeting Assistant API", lifespan=lifespan)


@app.middleware("http")
async def agent_debug_404_middleware(request: Request, call_next):
    response = await call_next(request)
    # #region agent log
    if response.status_code == 404 and "/api/settings" in request.url.path:
        _agent_debug_ndjson(
            "http_404_settings",
            {
                "path": request.url.path,
                "method": request.method,
                "query": str(request.url.query),
                "pid": os.getpid(),
            },
            "H4-H5",
        )
    # #endregion
    return response


def get_conn(request: Request):
    return request.app.state.conn


def get_lock(request: Request):
    return request.app.state.db_lock


ConnDep = Annotated[sqlite3.Connection, Depends(get_conn)]
LockDep = Annotated[threading.Lock, Depends(get_lock)]


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj)}\n\n"


@app.get("/api/health")
def api_health(conn: ConnDep):
    return health_snapshot(conn)


@app.get("/api/settings/llm", response_model=LlmSettingsOut)
def get_llm_settings(conn: ConnDep):
    return get_llm_settings_view(conn)


@app.patch("/api/settings/llm", response_model=LlmSettingsOut)
def update_llm_settings(conn: ConnDep, lock: LockDep, body: LlmSettingsPatch):
    updates = body.model_dump(exclude_unset=True)
    with lock:
        return apply_llm_settings_patch(conn, updates)


@app.get("/api/models")
def api_models(conn: ConnDep):
    """Expose active model IDs (DB overrides LLM; env is fallback)."""
    llm_id = get_effective_model_id(conn)
    return {
        "llm": {
            "active_id": llm_id,
            "role": "chat_rag_summarize",
            "environment_default": LLM_MODEL,
        },
        "whisper": {"active_id": WHISPER_MODEL},
        "embedding": {"active_id": EMBEDDING_MODEL},
        "note": "Override the chat LLM in Settings (chat gear icon) or set LLM_MODEL in the environment.",
    }


def _list_sessions(
    conn: sqlite3.Connection,
    session_type: str | None,
    limit: int,
    offset: int,
):
    svc = SessionService(conn)
    rows = svc.list_sessions(
        limit=min(limit, 500),
        offset=offset,
        session_type=session_type,
    )
    return [meeting_to_session_out(m) for m in rows]


@app.get("/api/sessions", response_model=list[SessionOut])
@app.get("/api/meetings", response_model=list[SessionOut])
def list_sessions(
    conn: ConnDep,
    session_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
):
    return _list_sessions(conn, session_type, limit, offset)


@app.get("/api/sessions/{session_id}", response_model=SessionOut)
@app.get("/api/meetings/{session_id}", response_model=SessionOut)
def get_session(conn: ConnDep, session_id: int):
    svc = SessionService(conn)
    m = svc.get(session_id)
    if not m:
        raise HTTPException(status_code=404, detail="Session not found")
    return meeting_to_session_out(m)


@app.patch("/api/sessions/{session_id}", response_model=SessionOut)
@app.patch("/api/meetings/{session_id}", response_model=SessionOut)
def patch_session(
    conn: ConnDep,
    lock: LockDep,
    session_id: int,
    body: SessionPatch,
):
    svc = SessionService(conn)
    if not svc.get(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        return meeting_to_session_out(svc.get(session_id))  # type: ignore[arg-type]
    with lock:
        svc.patch_session(session_id, updates)
    m = svc.get(session_id)
    assert m is not None
    return meeting_to_session_out(m)


@app.delete("/api/sessions/{session_id}", status_code=204)
@app.delete("/api/meetings/{session_id}", status_code=204)
def delete_session(conn: ConnDep, lock: LockDep, session_id: int):
    svc = SessionService(conn)
    if not svc.get(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    with lock:
        svc.delete_session(session_id)


@app.get("/api/sessions/{session_id}/segments", response_model=list[SegmentOut])
@app.get("/api/meetings/{session_id}/segments", response_model=list[SegmentOut])
def list_segments(conn: ConnDep, session_id: int):
    svc = SessionService(conn)
    if not svc.get(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    seg_repo = SegmentRepo(conn)
    segments = seg_repo.get_by_meeting(session_id)
    return [
        SegmentOut(
            id=s.id,
            meeting_id=s.meeting_id,
            sequence_num=s.sequence_num,
            text=s.text,
            start_ms=s.start_ms,
            end_ms=s.end_ms,
            speaker_label=s.speaker_label,
            confidence=s.confidence,
            created_at=s.created_at,
        )
        for s in segments
    ]


@app.post("/api/sessions/{session_id}/summarize")
@app.post("/api/meetings/{session_id}/summarize")
def summarize_session(
    conn: ConnDep,
    session_id: int,
    body: SummarizeBody | None = Body(default=None),
):
    """One-shot summary of all transcript segments (local LLM)."""
    max_chars = body.max_chars if body is not None else 32_000
    svc = SessionService(conn)
    if not svc.get(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    seg_repo = SegmentRepo(conn)
    segments = seg_repo.get_by_meeting(session_id)
    if not segments:
        raise HTTPException(
            status_code=400,
            detail="No transcript segments — record or import transcript first.",
        )
    text = "\n".join(s.text for s in segments)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[…truncated…]"
    messages = [
        {
            "role": "user",
            "content": (
                "Summarize the following transcript clearly and concisely. "
                "Use short sections or bullet points for main topics, decisions, "
                "and action items where appropriate.\n\n"
                + text
            ),
        }
    ]
    model_id = get_effective_model_id(conn)
    max_tok = min(2048, max(256, get_effective_max_new_tokens(conn)))
    llm = LLM(model_name=model_id)
    llm.load()
    summary = llm.generate(messages, max_tokens=max_tok)
    return {"summary": summary, "llm_model": model_id}


@app.post("/api/sessions/{session_id}/reindex")
@app.post("/api/meetings/{session_id}/reindex")
def reindex(conn: ConnDep, lock: LockDep, session_id: int):
    svc = SessionService(conn)
    if not svc.get(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    with lock:
        n = index_session(session_id, conn)
    return {"indexed_chunks": n}


@app.post("/api/sessions/{session_id}/chat")
@app.post("/api/meetings/{session_id}/chat")
def chat_stream(
    conn: ConnDep,
    lock: LockDep,
    session_id: int,
    body: ChatRequest,
):
    svc = SessionService(conn)
    if not svc.get(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    chat_repo = ChatRepo(conn)

    with lock:
        if body.chat_session_id is not None:
            db_session_id = body.chat_session_id
            sess = chat_repo.get_session(db_session_id)
            if not sess or sess.meeting_id != session_id:
                raise HTTPException(status_code=400, detail="Invalid chat_session_id")
        else:
            db_session_id = chat_repo.create_session(session_id)

        chat_repo.add_message(db_session_id, "user", body.message)

    prepare_exc: Exception | None = None
    prepared = None
    try:
        prepared = prepare_rag_stream(conn, session_id, body.message)
    except Exception as exc:
        prepare_exc = exc
        logging.exception("prepare_rag_stream failed for session_id=%s", session_id)
        # #region agent log
        _agent_debug_ndjson(
            "chat_prepare_rag_failed",
            {
                "session_id": session_id,
                "error_type": type(exc).__name__,
                "error_preview": str(exc)[:400],
                "pid": os.getpid(),
            },
            "rag-fail",
        )
        # #endregion

    def event_gen():
        if prepare_exc is not None:
            yield _sse(
                {
                    "error": "rag_prepare_failed",
                    "message": str(prepare_exc),
                }
            )
            return
        if prepared is None:
            yield _sse(
                {
                    "error": "no_chunks",
                    "message": "No relevant transcript segments. Record and index first.",
                }
            )
            return

        chunk_payload = [
            {
                "id": c.id,
                "chunk_index": c.chunk_index,
                "text": c.text if len(c.text) <= 1200 else c.text[:1200] + "…",
                "start_ms": c.start_ms,
                "end_ms": c.end_ms,
            }
            for c in prepared.chunks
        ]
        yield _sse(
            {
                "retrieval": {
                    "query": body.message,
                    "chunks": chunk_payload,
                    "llm_model": get_effective_model_id(conn),
                }
            }
        )

        full: list[str] = []
        try:
            for token in prepared.token_stream:
                full.append(token)
                yield _sse({"token": token})
        except Exception as exc:
            logging.exception("LLM token stream failed")
            yield _sse({"error": "generation_failed", "message": str(exc)})
            return

        text = "".join(full)
        with lock:
            chat_repo.add_message(
                db_session_id,
                "assistant",
                text,
                prepared.chunk_ids,
            )

        yield _sse(
            {
                "done": True,
                "chunk_ids": prepared.chunk_ids,
                "chat_session_id": db_session_id,
            }
        )

    return StreamingResponse(event_gen(), media_type="text/event-stream")


def main() -> None:
    host = os.environ.get("MEETING_API_HOST", "127.0.0.1")
    port = int(os.environ.get("MEETING_API_PORT", "8765"))
    uvicorn.run(
        "src.api.main:app",
        host=host,
        port=port,
        reload=False,
        factory=False,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
