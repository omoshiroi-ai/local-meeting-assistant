"""SQLite database setup — sessions and segments tables."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "meetings.db"


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT    NOT NULL DEFAULT 'Untitled',
            status      TEXT    NOT NULL DEFAULT 'pending',
            audio_path  TEXT,
            duration_secs INTEGER,
            error_msg   TEXT,
            created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            updated_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        );

        CREATE TABLE IF NOT EXISTS segments (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id   INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            sequence_num INTEGER NOT NULL,
            text         TEXT    NOT NULL,
            start_sec    REAL    NOT NULL,
            end_sec      REAL    NOT NULL,
            speaker      TEXT,
            created_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        );

        CREATE INDEX IF NOT EXISTS idx_segments_session ON segments(session_id);
    """)
    conn.commit()
