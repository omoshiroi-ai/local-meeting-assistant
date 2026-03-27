"""index_meeting — end-to-end post-recording indexing pipeline.

Call this from a background worker after a meeting ends:

    from src.indexing.pipeline import index_meeting
    index_meeting(meeting_id, conn)   # blocks; safe to run in a thread
"""

import logging
import sqlite3

from src.db.repository import ChunkRepo, SegmentRepo
from src.indexing.chunker import chunk_segments
from src.indexing.embedder import Embedder
from src.indexing.vector_store import VectorStore

logger = logging.getLogger(__name__)


def index_meeting(meeting_id: int, conn: sqlite3.Connection) -> int:
    """Chunk, embed, and index all segments for a meeting.

    Returns the number of chunks indexed.
    Idempotent: deletes existing chunks before re-indexing.
    """
    seg_repo = SegmentRepo(conn)
    chunk_repo = ChunkRepo(conn)

    segments = seg_repo.get_by_meeting(meeting_id)
    if not segments:
        logger.info("No segments to index for meeting %d", meeting_id)
        return 0

    logger.info(
        "Indexing meeting %d: %d segments", meeting_id, len(segments)
    )

    # --- Chunk ---
    chunk_dicts = chunk_segments(segments, meeting_id)
    if not chunk_dicts:
        return 0

    # Remove stale chunks (idempotent re-index)
    chunk_repo.delete_by_meeting(meeting_id)

    chunk_ids = chunk_repo.insert_many(chunk_dicts)
    texts = [c["text"] for c in chunk_dicts]

    # --- Embed ---
    embedder = Embedder()
    embedder.load()
    vectors = embedder.encode(texts)

    # --- Index ---
    store = VectorStore()
    store.load_or_create()
    row_ids = store.add(vectors, chunk_ids)
    store.save()

    # Update faiss_row_id back in DB
    chunk_repo.update_faiss_row_ids(dict(zip(chunk_ids, row_ids)))

    logger.info(
        "Meeting %d indexed: %d chunks, %d total vectors in store",
        meeting_id, len(chunk_ids), store.total,
    )
    return len(chunk_ids)
