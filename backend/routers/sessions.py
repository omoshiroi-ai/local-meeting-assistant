"""Session CRUD endpoints."""

from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def get_conn(request: Request) -> sqlite3.Connection:
    return request.app.state.conn


ConnDep = Annotated[sqlite3.Connection, Depends(get_conn)]


class SessionOut(BaseModel):
    id: int
    title: str
    status: str
    duration_secs: int | None
    error_msg: str | None
    created_at: str
    updated_at: str


class SegmentOut(BaseModel):
    id: int
    session_id: int
    sequence_num: int
    text: str
    start_sec: float
    end_sec: float
    speaker: str | None
    created_at: str


class SessionPatch(BaseModel):
    title: str | None = None


def _row_to_out(row: sqlite3.Row) -> SessionOut:
    return SessionOut(
        id=row["id"],
        title=row["title"],
        status=row["status"],
        duration_secs=row["duration_secs"],
        error_msg=row["error_msg"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("", response_model=list[SessionOut])
def list_sessions(conn: ConnDep, limit: int = 100, offset: int = 0):
    rows = conn.execute(
        "SELECT * FROM sessions ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (min(limit, 500), offset),
    ).fetchall()
    return [_row_to_out(r) for r in rows]


@router.get("/{session_id}", response_model=SessionOut)
def get_session(conn: ConnDep, session_id: int):
    row = conn.execute(
        "SELECT * FROM sessions WHERE id = ?", (session_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    return _row_to_out(row)


@router.patch("/{session_id}", response_model=SessionOut)
def patch_session(conn: ConnDep, session_id: int, body: SessionPatch):
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        return get_session(conn, session_id)
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [session_id]
    conn.execute(
        f"UPDATE sessions SET {set_clause}, updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
        values,
    )
    conn.commit()
    return get_session(conn, session_id)


@router.delete("/{session_id}", status_code=204)
def delete_session(conn: ConnDep, session_id: int):
    row = conn.execute(
        "SELECT id FROM sessions WHERE id = ?", (session_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    try:
        from backend.services.rag import delete_session as rag_delete
        rag_delete(session_id)
    except Exception:
        pass  # ChromaDB cleanup is best-effort


@router.get("/{session_id}/segments", response_model=list[SegmentOut])
def list_segments(conn: ConnDep, session_id: int):
    row = conn.execute(
        "SELECT id FROM sessions WHERE id = ?", (session_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    rows = conn.execute(
        "SELECT * FROM segments WHERE session_id = ? ORDER BY sequence_num",
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
