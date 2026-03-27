"""SQLite schema DDL. All CREATE TABLE statements live here."""

import sqlite3

# Increment this when adding new migrations in migrations.py
SCHEMA_VERSION = 1

DDL = """
CREATE TABLE IF NOT EXISTS meetings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL DEFAULT '',
    source          TEXT NOT NULL DEFAULT 'manual',
    started_at      TEXT NOT NULL,
    ended_at        TEXT,
    duration_secs   INTEGER GENERATED ALWAYS AS (
                        CAST((JULIANDAY(ended_at) - JULIANDAY(started_at)) * 86400 AS INTEGER)
                    ) VIRTUAL,
    notes           TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS transcript_segments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id      INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    sequence_num    INTEGER NOT NULL,
    speaker_label   TEXT,
    text            TEXT NOT NULL,
    start_ms        INTEGER NOT NULL,
    end_ms          INTEGER NOT NULL,
    confidence      REAL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(meeting_id, sequence_num)
);

CREATE TABLE IF NOT EXISTS transcript_chunks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id      INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    chunk_index     INTEGER NOT NULL,
    text            TEXT NOT NULL,
    start_ms        INTEGER NOT NULL,
    end_ms          INTEGER NOT NULL,
    token_count     INTEGER NOT NULL,
    embedding_dim   INTEGER NOT NULL DEFAULT 768,
    faiss_row_id    INTEGER,
    indexed_at      TEXT,
    UNIQUE(meeting_id, chunk_index)
);

CREATE TABLE IF NOT EXISTS chat_sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id      INTEGER REFERENCES meetings(id) ON DELETE SET NULL,
    started_at      TEXT NOT NULL DEFAULT (datetime('now')),
    ended_at        TEXT
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    content         TEXT NOT NULL,
    retrieved_chunk_ids TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS app_state (
    key             TEXT PRIMARY KEY,
    value           TEXT NOT NULL,
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_segments_meeting ON transcript_segments(meeting_id, sequence_num);
CREATE INDEX IF NOT EXISTS idx_chunks_meeting   ON transcript_chunks(meeting_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_chunks_faiss     ON transcript_chunks(faiss_row_id)
    WHERE faiss_row_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_messages_session ON chat_messages(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_meetings_started ON meetings(started_at DESC);
"""


def init_db(conn: sqlite3.Connection) -> None:
    """Create all tables and indexes. Safe to call on an existing database."""
    conn.executescript(DDL)
    conn.commit()
