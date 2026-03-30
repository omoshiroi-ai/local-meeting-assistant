"""Sync ChromaDB with the SQLite sessions database.

Ensures every completed session has up-to-date vector chunks.
Useful for backfilling after fresh setup, or after upgrading the embedding model.

Usage:
    uv run python scripts/reindex.py                   # sync all sessions
    uv run python scripts/reindex.py --session-id 42   # single session
    uv run python scripts/reindex.py --check           # report status without indexing
    uv run python scripts/reindex.py --reset           # wipe ChromaDB then reindex all
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# Ensure project root is on the path so `backend` package is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

# Must be set before any chromadb import
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")


def _get_db_sessions(conn, session_id: int | None) -> list:
    if session_id is not None:
        rows = conn.execute(
            "SELECT id, title, status FROM sessions WHERE id = ? AND status = 'done'",
            (session_id,),
        ).fetchall()
        if not rows:
            # Check if it exists but wrong status
            row = conn.execute("SELECT id, status FROM sessions WHERE id = ?", (session_id,)).fetchone()
            if row:
                print(f"  Session {session_id} has status '{row['status']}' — must be 'done' to index.",
                      file=sys.stderr)
            else:
                print(f"  Session {session_id} not found.", file=sys.stderr)
        return rows
    return conn.execute(
        "SELECT id, title, status FROM sessions WHERE status = 'done' ORDER BY id"
    ).fetchall()


def _get_segments(conn, session_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT text, start_sec, end_sec FROM segments WHERE session_id = ? ORDER BY sequence_num",
        (session_id,),
    ).fetchall()
    return [{"text": r["text"], "start_sec": r["start_sec"], "end_sec": r["end_sec"]} for r in rows]


def _indexed_session_ids(collection) -> set[int]:
    """Return the set of session_ids that have at least one chunk in ChromaDB."""
    result = collection.get(include=["metadatas"])
    ids: set[int] = set()
    for meta in result.get("metadatas") or []:
        if meta and "session_id" in meta:
            ids.add(int(meta["session_id"]))
    return ids


def cmd_check(conn, collection) -> None:
    sessions = _get_db_sessions(conn, session_id=None)
    indexed = _indexed_session_ids(collection)
    total_chunks = collection.count()

    print(f"\n  ChromaDB: {total_chunks} total chunks across {len(indexed)} session(s)")
    print(f"  SQLite  : {len(sessions)} completed session(s)\n")

    missing = []
    for row in sessions:
        sid = row["id"]
        marker = "[OK]" if sid in indexed else "[--]"
        seg_count = conn.execute(
            "SELECT COUNT(*) FROM segments WHERE session_id = ?", (sid,)
        ).fetchone()[0]
        print(f"  {marker}  session {sid:>4}  —  {row['title']!r}  ({seg_count} segments)")
        if sid not in indexed:
            missing.append(sid)

    print()
    if missing:
        print(f"  {len(missing)} session(s) not indexed. Run without --check to sync.")
    else:
        print("  All sessions are indexed.")
    print()


def cmd_reindex(conn, collection, session_id: int | None, reset: bool) -> None:
    from backend.services.rag import ingest_session

    if reset and session_id is None:
        print("  Wiping ChromaDB collection…", end=" ", flush=True)
        # Delete all documents
        all_ids = collection.get(include=[])["ids"]
        if all_ids:
            collection.delete(ids=all_ids)
        print(f"deleted {len(all_ids)} chunks.")

    sessions = _get_db_sessions(conn, session_id)
    if not sessions:
        print("  Nothing to index.")
        return

    print(f"  Indexing {len(sessions)} session(s)…\n")
    total_chunks = 0
    t0 = time.monotonic()

    for row in sessions:
        sid = row["id"]
        title = row["title"]
        segments = _get_segments(conn, sid)

        if not segments:
            print(f"  session {sid:>4}  —  {title!r}  → skipped (no segments)")
            continue

        print(f"  session {sid:>4}  —  {title!r}  ({len(segments)} segments)… ", end="", flush=True)
        t1 = time.monotonic()
        n = ingest_session(session_id=sid, session_title=title, segments=segments)
        print(f"{n} chunks ({time.monotonic() - t1:.1f}s)")
        total_chunks += n

    elapsed = time.monotonic() - t0
    print(f"\n  Done: {total_chunks} chunks indexed in {elapsed:.1f}s")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync ChromaDB vector store with SQLite sessions.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--session-id", type=int, default=None, metavar="ID",
        help="Only process this session (default: all completed sessions).",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Report which sessions are indexed without making changes.",
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="Wipe ChromaDB and reindex from scratch (all sessions only).",
    )
    args = parser.parse_args()

    if args.reset and args.session_id is not None:
        print("--reset and --session-id cannot be used together.", file=sys.stderr)
        sys.exit(1)

    width = 60
    print("=" * width)
    print("  Local Meeting Assistant — ChromaDB Sync")
    print("=" * width)

    from backend.db import connect
    from backend.services.rag import get_collection

    conn = connect()
    collection = get_collection()

    if args.check:
        cmd_check(conn, collection)
    else:
        cmd_reindex(conn, collection, session_id=args.session_id, reset=args.reset)

    conn.close()
    print("=" * width + "\n")


if __name__ == "__main__":
    main()
