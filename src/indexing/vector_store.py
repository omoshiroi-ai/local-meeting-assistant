"""VectorStore — FAISS IndexFlatIP wrapper with disk persistence.

Vectors must be L2-normalised before insertion (inner product == cosine sim).

The index file and a companion JSON metadata file are persisted to
FAISS_INDEX_PATH / FAISS_META_PATH from src/config.py.

Usage::

    store = VectorStore()
    store.load_or_create()
    row_ids = store.add(vectors)          # numpy (N, D) float32
    chunk_ids = store.search(query, k=5)  # returns DB chunk IDs
    store.save()
"""

import json
import logging
from pathlib import Path

import faiss
import numpy as np

from src.config import EMBEDDING_DIM, FAISS_INDEX_PATH, FAISS_META_PATH

logger = logging.getLogger(__name__)


class VectorStore:
    """Thin wrapper around faiss.IndexFlatIP with chunk-ID metadata."""

    def __init__(self) -> None:
        self._index: faiss.IndexFlatIP | None = None
        # Maps FAISS row index → DB chunk id
        self._row_to_chunk: list[int] = []

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def load_or_create(self) -> None:
        """Load existing index from disk, or create a fresh one."""
        if FAISS_INDEX_PATH.exists() and FAISS_META_PATH.exists():
            logger.info("Loading FAISS index from %s", FAISS_INDEX_PATH)
            self._index = faiss.read_index(str(FAISS_INDEX_PATH))
            self._row_to_chunk = json.loads(FAISS_META_PATH.read_text())
            logger.info("Loaded %d vectors", self._index.ntotal)
        else:
            logger.info("Creating new FAISS IndexFlatIP (dim=%d)", EMBEDDING_DIM)
            self._index = faiss.IndexFlatIP(EMBEDDING_DIM)
            self._row_to_chunk = []

    def save(self) -> None:
        """Persist index and metadata to disk."""
        if self._index is None:
            return
        FAISS_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(FAISS_INDEX_PATH))
        FAISS_META_PATH.write_text(json.dumps(self._row_to_chunk))
        logger.info("Saved FAISS index (%d vectors)", self._index.ntotal)

    # ------------------------------------------------------------------ #
    # Read / write
    # ------------------------------------------------------------------ #

    def add(self, vectors: np.ndarray, chunk_ids: list[int]) -> list[int]:
        """Add L2-normalised vectors and associate them with DB chunk IDs.

        Returns the FAISS row IDs assigned to each vector.
        """
        assert self._index is not None, "call load_or_create() first"
        assert vectors.shape == (len(chunk_ids), EMBEDDING_DIM)

        start_row = self._index.ntotal
        self._index.add(vectors.astype(np.float32))
        row_ids = list(range(start_row, start_row + len(chunk_ids)))
        self._row_to_chunk.extend(chunk_ids)

        logger.debug("Added %d vectors (total: %d)", len(chunk_ids), self._index.ntotal)
        return row_ids

    def search(self, query_vector: np.ndarray, k: int = 5) -> list[int]:
        """Search for the k nearest chunks.

        query_vector: shape (D,) or (1, D), L2-normalised float32.
        Returns a list of DB chunk IDs (may be shorter than k if index is small).
        """
        assert self._index is not None, "call load_or_create() first"
        if self._index.ntotal == 0:
            return []

        qv = query_vector.reshape(1, -1).astype(np.float32)
        k = min(k, self._index.ntotal)
        _, indices = self._index.search(qv, k)

        chunk_ids = []
        for row in indices[0]:
            if row >= 0 and row < len(self._row_to_chunk):
                chunk_ids.append(self._row_to_chunk[row])
        return chunk_ids

    @property
    def total(self) -> int:
        return self._index.ntotal if self._index else 0
