"""Rebuild the FAISS index from all meetings in the DB.

Use this after upgrading the embedding model or if the index gets corrupted.

    uv run python scripts/reindex.py
    uv run python scripts/reindex.py --meeting-id 42   # single meeting
"""

import argparse
import sys
import time


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild FAISS index from DB segments.")
    parser.add_argument("--meeting-id", type=int, default=None,
                        help="Re-index a single meeting (default: all meetings).")
    args = parser.parse_args()

    from src.config import FAISS_INDEX_PATH, FAISS_META_PATH
    from src.db.repository import MeetingRepo
    from src.indexing.pipeline import index_meeting
    from src.main import get_connection

    conn = get_connection()

    # Wipe index if re-indexing all meetings
    if args.meeting_id is None:
        FAISS_INDEX_PATH.unlink(missing_ok=True)
        FAISS_META_PATH.unlink(missing_ok=True)
        print("Wiped existing FAISS index.")

    meeting_repo = MeetingRepo(conn)

    if args.meeting_id:
        meeting_ids = [args.meeting_id]
    else:
        meetings = meeting_repo.list_all(limit=10000)
        meeting_ids = [m.id for m in meetings]

    if not meeting_ids:
        print("No meetings found.")
        sys.exit(0)

    print(f"Re-indexing {len(meeting_ids)} meeting(s)…")
    total_chunks = 0
    t0 = time.monotonic()

    for mid in meeting_ids:
        print(f"  Meeting {mid}… ", end="", flush=True)
        n = index_meeting(mid, conn)
        print(f"{n} chunks")
        total_chunks += n

    elapsed = time.monotonic() - t0
    print(f"\nDone: {total_chunks} chunks in {elapsed:.1f}s")
    conn.close()


if __name__ == "__main__":
    main()
