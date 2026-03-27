"""Retriever — embed a query and fetch the top-k transcript chunks from FAISS.

Usage::

    retriever = Retriever(conn)
    retriever.load()
    chunks = retriever.retrieve("What was decided about the roadmap?", k=5)
"""

import logging
import sqlite3

from src.config import RAG_TOP_K
from src.db.repository import ChunkRepo, TranscriptChunk
from src.indexing.embedder import Embedder
from src.indexing.vector_store import VectorStore

logger = logging.getLogger(__name__)


class Retriever:
    """Embeds a query and returns the most relevant TranscriptChunks."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._embedder = Embedder()
        self._store = VectorStore()
        self._loaded = False

    def load(self) -> None:
        """Load the embedding model and FAISS index. Safe to call multiple times."""
        if self._loaded:
            return
        self._embedder.load()
        self._store.load_or_create()
        self._loaded = True

    def retrieve(
        self,
        query: str,
        k: int = RAG_TOP_K,
        meeting_id: int | None = None,
    ) -> list[TranscriptChunk]:
        """Return the top-k chunks most relevant to query.

        If meeting_id is given, results are filtered to that meeting only
        (post-filter: retrieves k*3 then filters, to keep good recall).
        """
        if not self._loaded:
            self.load()

        # nomic-embed-text uses search_query prefix for retrieval queries
        vec = self._embedder._model.encode(  # type: ignore[union-attr]
            f"search_query: {query}",
            normalize_embeddings=True,
            show_progress_bar=False,
        ).astype("float32")

        fetch_k = k * 3 if meeting_id is not None else k
        chunk_ids = self._store.search(vec, k=fetch_k)

        if not chunk_ids:
            return []

        chunk_repo = ChunkRepo(self._conn)
        chunks = chunk_repo.get_by_ids(chunk_ids)

        if meeting_id is not None:
            chunks = [c for c in chunks if c.meeting_id == meeting_id]

        # Preserve FAISS ranking order, trim to k
        id_order = {cid: i for i, cid in enumerate(chunk_ids)}
        chunks.sort(key=lambda c: id_order.get(c.id, 9999))
        chunks = chunks[:k]

        logger.debug("Retrieved %d chunks for query %r", len(chunks), query[:60])
        return chunks
