"""Shared SQLite connection factory."""

import sqlite3

from src.config import DB_PATH


def connect(*, check_same_thread: bool = True) -> sqlite3.Connection:
    """Open DB with WAL + foreign keys. Use check_same_thread=False for FastAPI."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=check_same_thread)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
