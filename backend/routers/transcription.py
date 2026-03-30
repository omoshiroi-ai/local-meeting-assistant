"""Upload audio and transcribe endpoints."""

from __future__ import annotations

import asyncio
import logging
import sqlite3
import threading
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from pydantic import BaseModel

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(__file__).parent.parent.parent / "data" / "uploads"

router = APIRouter(prefix="/api", tags=["transcription"])


def get_conn(request: Request) -> sqlite3.Connection:
    return request.app.state.conn


ConnDep = Annotated[sqlite3.Connection, Depends(get_conn)]


class SegmentOut(BaseModel):
    id: int
    session_id: int
    sequence_num: int
    text: str
    start_sec: float
    end_sec: float
    speaker: str | None
    created_at: str


@router.post("/sessions/upload", status_code=202)
async def upload_audio(request: Request, file: UploadFile, conn: ConnDep):
    """
    Upload an audio file. Creates a session with status=pending,
    then kicks off transcription in a background thread.

    Returns the session_id immediately — poll GET /api/sessions/{id} for status.
    """
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # Determine safe filename
    original = Path(file.filename or "recording.webm")
    suffix = original.suffix or ".webm"

    # Create session row first to get an ID
    cur = conn.execute(
        "INSERT INTO sessions (title, status) VALUES (?, 'pending') RETURNING id",
        (original.stem or "Recording",),
    )
    session_id: int = cur.fetchone()["id"]
    conn.commit()

    # Save audio file
    audio_path = UPLOAD_DIR / f"{session_id}{suffix}"
    content = await file.read()
    audio_path.write_bytes(content)

    # Store audio_path in DB
    conn.execute(
        "UPDATE sessions SET audio_path = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
        (str(audio_path), session_id),
    )
    conn.commit()

    # Start transcription in a background thread so we return immediately
    thread = threading.Thread(
        target=_run_transcription,
        args=(session_id, str(audio_path)),
        daemon=True,
    )
    thread.start()

    return {"session_id": session_id, "status": "pending"}


def _run_transcription(session_id: int, audio_path: str) -> None:
    """Background worker: transcribe audio and write segments to DB."""
    from backend.db import connect
    from backend.services.transcriber import transcribe

    conn = connect()
    try:
        conn.execute(
            "UPDATE sessions SET status='transcribing', updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id=?",
            (session_id,),
        )
        conn.commit()

        segments = transcribe(audio_path)

        for i, seg in enumerate(segments):
            conn.execute(
                "INSERT INTO segments (session_id, sequence_num, text, start_sec, end_sec) VALUES (?,?,?,?,?)",
                (session_id, i, seg["text"], seg["start_sec"], seg["end_sec"]),
            )

        conn.execute(
            "UPDATE sessions SET status='done', updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id=?",
            (session_id,),
        )
        conn.commit()
        logger.info("Transcription done for session %d: %d segments", session_id, len(segments))

        # Index into ChromaDB for RAG
        try:
            session_row = conn.execute(
                "SELECT title FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
            session_title = session_row["title"] if session_row else f"Session {session_id}"
            from backend.services.rag import ingest_session
            ingest_session(session_id=session_id, session_title=session_title, segments=segments)
        except Exception:
            logger.exception("RAG indexing failed for session %d (transcription still succeeded)", session_id)

    except Exception as exc:
        logger.exception("Transcription failed for session %d", session_id)
        conn.execute(
            "UPDATE sessions SET status='error', error_msg=?, updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id=?",
            (str(exc), session_id),
        )
        conn.commit()
    finally:
        conn.close()


@router.get("/sessions/{session_id}/segments", response_model=list[SegmentOut])
def list_segments(conn: ConnDep, session_id: int):
    row = conn.execute("SELECT id FROM sessions WHERE id=?", (session_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    rows = conn.execute(
        "SELECT * FROM segments WHERE session_id=? ORDER BY sequence_num",
        (session_id,),
    ).fetchall()
    return [
        SegmentOut(
            id=r["id"],
            session_id=r["session_id"],
            sequence_num=r["sequence_num"],
            text=r["text"],
            start_sec=r["start_sec"],
            end_sec=r["end_sec"],
            speaker=r["speaker"],
            created_at=r["created_at"],
        )
        for r in rows
    ]
