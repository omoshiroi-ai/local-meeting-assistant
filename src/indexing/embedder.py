"""Embedder — nomic-embed-text wrapper via sentence-transformers.

sentence-transformers handles mean-pooling and L2-normalisation internally.
On Apple Silicon it uses the MPS backend automatically.

Usage::

    emb = Embedder()
    emb.load()                        # once per session
    vecs = emb.encode(["hello", …])   # (N, 768) float32 numpy array
"""

import logging

import numpy as np

from src.config import EMBEDDING_DIM, EMBEDDING_MODEL

logger = logging.getLogger(__name__)


class Embedder:
    """Wraps sentence-transformers SentenceTransformer for nomic-embed-text."""

    def __init__(self, model_name: str = EMBEDDING_MODEL) -> None:
        self._model_name = model_name
        self._model = None

    def load(self) -> None:
        """Load the embedding model. Safe to call multiple times."""
        if self._model is not None:
            return

        from sentence_transformers import SentenceTransformer

        logger.info("Loading embedding model: %s", self._model_name)
        # trust_remote_code required by nomic-embed-text-v1.5
        self._model = SentenceTransformer(
            self._model_name,
            trust_remote_code=True,
        )
        logger.info("Embedding model ready.")

    def encode(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        """Encode texts into L2-normalised float32 vectors.

        Returns shape (N, EMBEDDING_DIM).
        nomic-embed-text uses a search_document prefix for indexing.
        """
        if self._model is None:
            self.load()

        # nomic-embed-text uses task-specific prefixes
        prefixed = [f"search_document: {t}" for t in texts]

        vecs = self._model.encode(  # type: ignore[union-attr]
            prefixed,
            batch_size=batch_size,
            normalize_embeddings=True,   # L2-normalise for cosine via IndexFlatIP
            show_progress_bar=False,
        )

        result = np.array(vecs, dtype=np.float32)
        assert result.shape == (len(texts), EMBEDDING_DIM), (
            f"Expected ({len(texts)}, {EMBEDDING_DIM}), got {result.shape}"
        )

        logger.debug("Encoded %d texts → shape %s", len(texts), result.shape)
        return result

    @property
    def is_loaded(self) -> bool:
        return self._model is not None
