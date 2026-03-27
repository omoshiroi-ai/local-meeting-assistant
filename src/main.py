"""Entrypoint for the local meeting assistant."""

import sqlite3

from src.config import DATA_DIR, DB_PATH, FAISS_DIR
from src.db.migrations import run_migrations
from src.db.schema import init_db


def _ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    FAISS_DIR.mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    """Return a configured SQLite connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def main() -> None:
    _ensure_dirs()
    from src.ui.app import MeetingAssistantApp

    app = MeetingAssistantApp()
    app.run()


if __name__ == "__main__":
    main()
