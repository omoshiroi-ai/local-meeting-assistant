"""Thin SSOT-facing API over MeetingRepo (sessions stored in `meetings` table)."""

from __future__ import annotations

import sqlite3
from typing import Any

from src.db.repository import Meeting, MeetingRepo


class SessionService:
    """Naming aligns with plan (`session` = one recording); DB table remains `meetings`."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._meetings = MeetingRepo(conn)

    def get(self, session_id: int) -> Meeting | None:
        return self._meetings.get(session_id)

    def list_sessions(
        self,
        limit: int = 100,
        offset: int = 0,
        session_type: str | None = None,
    ) -> list[Meeting]:
        return self._meetings.list_all(
            limit=limit, offset=offset, session_type=session_type
        )

    def delete_session(self, session_id: int) -> None:
        self._meetings.delete(session_id)

    def patch_session(self, session_id: int, updates: dict[str, Any]) -> None:
        self._meetings.patch_meeting(session_id, updates)
