"""Version-tracked schema migrations.

Each entry in MIGRATIONS is a (version, sql) tuple. The runner applies all
migrations with version > current PRAGMA user_version in order.

To add a migration:
  1. Append a new (N, "ALTER TABLE ...") entry to MIGRATIONS.
  2. Bump SCHEMA_VERSION in schema.py to N.
"""

import logging
import sqlite3

logger = logging.getLogger(__name__)

# List of (version, sql) pairs. Versions must be strictly increasing.
# Version 2 uses Python (see _apply_migration_v2) so existing DBs without new
# columns never hit CREATE INDEX on session_type before ALTERs (see init_db DDL).
MIGRATIONS: list[tuple[int, str | None]] = [
    (2, None),
]


def _meeting_column_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("PRAGMA table_info(meetings)").fetchall()
    return {str(r[1]) for r in rows}


def _apply_migration_v2(conn: sqlite3.Connection) -> None:
    """Add SSOT columns to ``meetings`` if missing; create session_type index."""
    cols = _meeting_column_names(conn)
    if "session_type" not in cols:
        conn.execute(
            "ALTER TABLE meetings ADD COLUMN session_type TEXT NOT NULL DEFAULT 'meeting'"
        )
    if "department_id" not in cols:
        conn.execute("ALTER TABLE meetings ADD COLUMN department_id INTEGER")
    if "metadata" not in cols:
        conn.execute("ALTER TABLE meetings ADD COLUMN metadata TEXT")
    if "wbs_node_id" not in cols:
        conn.execute("ALTER TABLE meetings ADD COLUMN wbs_node_id INTEGER")
    if "case_id" not in cols:
        conn.execute("ALTER TABLE meetings ADD COLUMN case_id TEXT")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_meetings_session_type ON meetings(session_type)"
    )


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
        if version == 2 and sql is None:
            _apply_migration_v2(conn)
        elif sql:
            conn.executescript(sql)
        else:
            raise RuntimeError(f"No handler for migration version {version}")
        set_user_version(conn, version)
        conn.commit()
        logger.info("Migration to version %d complete", version)
