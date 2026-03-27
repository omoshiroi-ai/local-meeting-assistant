"""Version-tracked schema migrations.

Each entry in MIGRATIONS is a (version, sql) tuple. The runner applies all
migrations with version > current PRAGMA user_version in order.

To add a migration:
  1. Append a new (N, "ALTER TABLE ...") entry to MIGRATIONS.
  2. Bump SCHEMA_VERSION in schema.py to N.
"""

import sqlite3
import logging

logger = logging.getLogger(__name__)

# List of (version, sql) pairs. Versions must be strictly increasing.
MIGRATIONS: list[tuple[int, str]] = [
    # Version 1: initial schema — handled by schema.init_db(), nothing to migrate.
    # Future migrations go here, e.g.:
    # (2, "ALTER TABLE meetings ADD COLUMN language TEXT NOT NULL DEFAULT 'en'"),
]


def get_user_version(conn: sqlite3.Connection) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]


def set_user_version(conn: sqlite3.Connection, version: int) -> None:
    # PRAGMA user_version doesn't support parameterized queries
    conn.execute(f"PRAGMA user_version = {version}")


def run_migrations(conn: sqlite3.Connection) -> None:
    """Apply any pending migrations in order."""
    current = get_user_version(conn)
    pending = [(v, sql) for v, sql in MIGRATIONS if v > current]

    if not pending:
        return

    for version, sql in pending:
        logger.info("Applying migration to version %d", version)
        conn.executescript(sql)
        set_user_version(conn, version)
        conn.commit()
        logger.info("Migration to version %d complete", version)
