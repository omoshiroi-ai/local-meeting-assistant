"""Database repository layer. All SQL lives here — no SQL in other modules.

Usage:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    meetings = MeetingRepo(conn)
    meeting_id = meetings.create("Weekly Sync", source="zoom")
"""

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Dataclasses (lightweight value objects, not ORM models)
# ---------------------------------------------------------------------------


@dataclass
class Meeting:
    id: int
    title: str
    source: str
    started_at: str
    ended_at: str | None
    duration_secs: int | None
    notes: str
    created_at: str
    updated_at: str


@dataclass
class TranscriptSegment:
    id: int
    meeting_id: int
    sequence_num: int
    text: str
    start_ms: int
    end_ms: int
    speaker_label: str | None = None
    confidence: float | None = None
    created_at: str = ""


@dataclass
class TranscriptChunk:
    id: int
    meeting_id: int
    chunk_index: int
    text: str
    start_ms: int
    end_ms: int
    token_count: int
    embedding_dim: int = 768
    faiss_row_id: int | None = None
    indexed_at: str | None = None


@dataclass
class ChatSession:
    id: int
    meeting_id: int | None
    started_at: str
    ended_at: str | None


@dataclass
class ChatMessage:
    id: int
    session_id: int
    role: str
    content: str
    retrieved_chunk_ids: list[int] = field(default_factory=list)
    created_at: str = ""


# ---------------------------------------------------------------------------
# Repositories
# ---------------------------------------------------------------------------


class MeetingRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(self, title: str = "", source: str = "manual") -> int:
        """Insert a new meeting and return its id."""
        cur = self._conn.execute(
            "INSERT INTO meetings (title, source, started_at) VALUES (?, ?, ?)",
            (title, source, _now()),
        )
        self._conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def end(self, meeting_id: int) -> None:
        """Set ended_at to now."""
        self._conn.execute(
            "UPDATE meetings SET ended_at = ?, updated_at = ? WHERE id = ?",
            (_now(), _now(), meeting_id),
        )
        self._conn.commit()

    def update_title(self, meeting_id: int, title: str) -> None:
        self._conn.execute(
            "UPDATE meetings SET title = ?, updated_at = ? WHERE id = ?",
            (title, _now(), meeting_id),
        )
        self._conn.commit()

    def update_notes(self, meeting_id: int, notes: str) -> None:
        self._conn.execute(
            "UPDATE meetings SET notes = ?, updated_at = ? WHERE id = ?",
            (notes, _now(), meeting_id),
        )
        self._conn.commit()

    def get(self, meeting_id: int) -> Meeting | None:
        row = self._conn.execute(
            "SELECT id, title, source, started_at, ended_at, duration_secs, "
            "notes, created_at, updated_at FROM meetings WHERE id = ?",
            (meeting_id,),
        ).fetchone()
        return _row_to_meeting(row) if row else None

    def list_all(self, limit: int = 100, offset: int = 0) -> list[Meeting]:
        rows = self._conn.execute(
            "SELECT id, title, source, started_at, ended_at, duration_secs, "
            "notes, created_at, updated_at FROM meetings "
            "ORDER BY started_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [_row_to_meeting(r) for r in rows]

    def delete(self, meeting_id: int) -> None:
        self._conn.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))
        self._conn.commit()

    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM meetings").fetchone()[0]


class SegmentRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def insert(
        self,
        meeting_id: int,
        sequence_num: int,
        text: str,
        start_ms: int,
        end_ms: int,
        speaker_label: str | None = None,
        confidence: float | None = None,
    ) -> int:
        cur = self._conn.execute(
            "INSERT INTO transcript_segments "
            "(meeting_id, sequence_num, text, start_ms, end_ms, speaker_label, confidence) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (meeting_id, sequence_num, text, start_ms, end_ms, speaker_label, confidence),
        )
        self._conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def get_by_meeting(self, meeting_id: int) -> list[TranscriptSegment]:
        rows = self._conn.execute(
            "SELECT id, meeting_id, sequence_num, text, start_ms, end_ms, "
            "speaker_label, confidence, created_at "
            "FROM transcript_segments WHERE meeting_id = ? ORDER BY sequence_num",
            (meeting_id,),
        ).fetchall()
        return [_row_to_segment(r) for r in rows]

    def next_sequence_num(self, meeting_id: int) -> int:
        """Return the next available sequence number for a meeting."""
        row = self._conn.execute(
            "SELECT COALESCE(MAX(sequence_num), -1) FROM transcript_segments WHERE meeting_id = ?",
            (meeting_id,),
        ).fetchone()
        return row[0] + 1

    def count_by_meeting(self, meeting_id: int) -> int:
        return self._conn.execute(
            "SELECT COUNT(*) FROM transcript_segments WHERE meeting_id = ?",
            (meeting_id,),
        ).fetchone()[0]


class ChunkRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def insert_many(self, chunks: list[dict]) -> list[int]:
        """Insert multiple chunks. Each dict must have keys matching the table columns.

        Required keys: meeting_id, chunk_index, text, start_ms, end_ms, token_count
        Optional keys: embedding_dim (default 768)
        """
        ids = []
        for chunk in chunks:
            cur = self._conn.execute(
                "INSERT INTO transcript_chunks "
                "(meeting_id, chunk_index, text, start_ms, end_ms, token_count, embedding_dim) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    chunk["meeting_id"],
                    chunk["chunk_index"],
                    chunk["text"],
                    chunk["start_ms"],
                    chunk["end_ms"],
                    chunk["token_count"],
                    chunk.get("embedding_dim", 768),
                ),
            )
            ids.append(cur.lastrowid)
        self._conn.commit()
        return ids  # type: ignore[return-value]

    def update_faiss_row_ids(self, chunk_id_to_faiss_row: dict[int, int]) -> None:
        """Update faiss_row_id and indexed_at for a batch of chunks."""
        now = _now()
        self._conn.executemany(
            "UPDATE transcript_chunks SET faiss_row_id = ?, indexed_at = ? WHERE id = ?",
            [(faiss_row, now, chunk_id) for chunk_id, faiss_row in chunk_id_to_faiss_row.items()],
        )
        self._conn.commit()

    def get_by_ids(self, chunk_ids: list[int]) -> list[TranscriptChunk]:
        if not chunk_ids:
            return []
        placeholders = ",".join("?" * len(chunk_ids))
        rows = self._conn.execute(
            f"SELECT id, meeting_id, chunk_index, text, start_ms, end_ms, token_count, "
            f"embedding_dim, faiss_row_id, indexed_at FROM transcript_chunks "
            f"WHERE id IN ({placeholders})",
            chunk_ids,
        ).fetchall()
        return [_row_to_chunk(r) for r in rows]

    def get_by_meeting(self, meeting_id: int) -> list[TranscriptChunk]:
        rows = self._conn.execute(
            "SELECT id, meeting_id, chunk_index, text, start_ms, end_ms, token_count, "
            "embedding_dim, faiss_row_id, indexed_at FROM transcript_chunks "
            "WHERE meeting_id = ? ORDER BY chunk_index",
            (meeting_id,),
        ).fetchall()
        return [_row_to_chunk(r) for r in rows]

    def delete_by_meeting(self, meeting_id: int) -> None:
        """Remove all chunks for a meeting (used by reindex script)."""
        self._conn.execute(
            "DELETE FROM transcript_chunks WHERE meeting_id = ?", (meeting_id,)
        )
        self._conn.commit()

    def get_unindexed(self) -> list[TranscriptChunk]:
        rows = self._conn.execute(
            "SELECT id, meeting_id, chunk_index, text, start_ms, end_ms, token_count, "
            "embedding_dim, faiss_row_id, indexed_at FROM transcript_chunks "
            "WHERE indexed_at IS NULL ORDER BY meeting_id, chunk_index",
        ).fetchall()
        return [_row_to_chunk(r) for r in rows]


class ChatRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create_session(self, meeting_id: int | None = None) -> int:
        cur = self._conn.execute(
            "INSERT INTO chat_sessions (meeting_id) VALUES (?)", (meeting_id,)
        )
        self._conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def end_session(self, session_id: int) -> None:
        self._conn.execute(
            "UPDATE chat_sessions SET ended_at = ? WHERE id = ?", (_now(), session_id)
        )
        self._conn.commit()

    def add_message(
        self,
        session_id: int,
        role: str,
        content: str,
        retrieved_chunk_ids: list[int] | None = None,
    ) -> int:
        chunk_ids_json = json.dumps(retrieved_chunk_ids) if retrieved_chunk_ids else None
        cur = self._conn.execute(
            "INSERT INTO chat_messages (session_id, role, content, retrieved_chunk_ids) "
            "VALUES (?, ?, ?, ?)",
            (session_id, role, content, chunk_ids_json),
        )
        self._conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def get_messages(self, session_id: int) -> list[ChatMessage]:
        rows = self._conn.execute(
            "SELECT id, session_id, role, content, retrieved_chunk_ids, created_at "
            "FROM chat_messages WHERE session_id = ? ORDER BY created_at",
            (session_id,),
        ).fetchall()
        return [_row_to_message(r) for r in rows]

    def get_session(self, session_id: int) -> ChatSession | None:
        row = self._conn.execute(
            "SELECT id, meeting_id, started_at, ended_at FROM chat_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        return _row_to_session(row) if row else None


class AppStateRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def set(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT INTO app_state (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
            (key, value, _now()),
        )
        self._conn.commit()

    def get(self, key: str, default: str | None = None) -> str | None:
        row = self._conn.execute(
            "SELECT value FROM app_state WHERE key = ?", (key,)
        ).fetchone()
        return row[0] if row else default

    def delete(self, key: str) -> None:
        self._conn.execute("DELETE FROM app_state WHERE key = ?", (key,))
        self._conn.commit()


# ---------------------------------------------------------------------------
# Private row mappers
# ---------------------------------------------------------------------------


def _row_to_meeting(row: sqlite3.Row) -> Meeting:
    return Meeting(
        id=row[0],
        title=row[1],
        source=row[2],
        started_at=row[3],
        ended_at=row[4],
        duration_secs=row[5],
        notes=row[6],
        created_at=row[7],
        updated_at=row[8],
    )


def _row_to_segment(row: sqlite3.Row) -> TranscriptSegment:
    return TranscriptSegment(
        id=row[0],
        meeting_id=row[1],
        sequence_num=row[2],
        text=row[3],
        start_ms=row[4],
        end_ms=row[5],
        speaker_label=row[6],
        confidence=row[7],
        created_at=row[8],
    )


def _row_to_chunk(row: sqlite3.Row) -> TranscriptChunk:
    return TranscriptChunk(
        id=row[0],
        meeting_id=row[1],
        chunk_index=row[2],
        text=row[3],
        start_ms=row[4],
        end_ms=row[5],
        token_count=row[6],
        embedding_dim=row[7],
        faiss_row_id=row[8],
        indexed_at=row[9],
    )


def _row_to_message(row: sqlite3.Row) -> ChatMessage:
    chunk_ids = json.loads(row[4]) if row[4] else []
    return ChatMessage(
        id=row[0],
        session_id=row[1],
        role=row[2],
        content=row[3],
        retrieved_chunk_ids=chunk_ids,
        created_at=row[5],
    )


def _row_to_session(row: sqlite3.Row) -> ChatSession:
    return ChatSession(
        id=row[0],
        meeting_id=row[1],
        started_at=row[2],
        ended_at=row[3],
    )
