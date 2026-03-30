"""RAG management endpoints: manual indexing for backfill and collection stats."""

from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/rag", tags=["rag"])


def get_conn(request: Request) -> sqlite3.Connection:
    return request.app.state.conn


ConnDep = Annotated[sqlite3.Connection, Depends(get_conn)]


class IndexResult(BaseModel):
    session_id: int
    chunks_indexed: int


@router.post("/index/{session_id}", response_model=IndexResult)
def index_session(conn: ConnDep, session_id: int):
    """
    Manually (re-)index a session into ChromaDB.
    Useful for backfilling sessions that existed before RAG was added.
    """
    row = conn.execute(
        "SELECT id, title, status FROM sessions WHERE id = ?", (session_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    if row["status"] != "done":
        raise HTTPException(
            status_code=400,
            detail=f"Session status is '{row['status']}', must be 'done' to index",
        )

    segments = conn.execute(
        "SELECT text, start_sec, end_sec FROM segments WHERE session_id = ? ORDER BY sequence_num",
        (session_id,),
    ).fetchall()

    from backend.services.rag import ingest_session

    n = ingest_session(
        session_id=session_id,
        session_title=row["title"],
        segments=[
            {"text": s["text"], "start_sec": s["start_sec"], "end_sec": s["end_sec"]}
            for s in segments
        ],
    )
    return IndexResult(session_id=session_id, chunks_indexed=n)


@router.post("/index", response_model=list[IndexResult])
def index_all_sessions(conn: ConnDep):
    """Backfill all completed sessions into ChromaDB."""
    rows = conn.execute(
        "SELECT id FROM sessions WHERE status = 'done'"
    ).fetchall()

    results = []
    for row in rows:
        segments = conn.execute(
            "SELECT text, start_sec, end_sec FROM segments WHERE session_id = ? ORDER BY sequence_num",
            (row["id"],),
        ).fetchall()
        session = conn.execute(
            "SELECT id, title FROM sessions WHERE id = ?", (row["id"],)
        ).fetchone()

        from backend.services.rag import ingest_session

        n = ingest_session(
            session_id=session["id"],
            session_title=session["title"],
            segments=[
                {"text": s["text"], "start_sec": s["start_sec"], "end_sec": s["end_sec"]}
                for s in segments
            ],
        )
        results.append(IndexResult(session_id=session["id"], chunks_indexed=n))

    return results


@router.get("/stats")
def rag_stats():
    from backend.services.rag import get_stats

    return get_stats()
