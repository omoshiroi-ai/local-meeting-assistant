"""Embedder — MLX nomic-embed-text wrapper.

Encodes text chunks into L2-normalised float32 vectors for FAISS IndexFlatIP
(inner-product on normalised vectors == cosine similarity).

Designed to be called from a worker thread (blocking MLX call).

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
    """Wraps mlx-lm's text embedding pipeline for nomic-embed-text."""

    def __init__(self, model_name: str = EMBEDDING_MODEL) -> None:
        self._model_name = model_name
        self._pipeline = None

    def load(self) -> None:
        """Load the embedding model. Safe to call multiple times."""
        if self._pipeline is not None:
            return

        from huggingface_hub import snapshot_download
        from huggingface_hub.utils import LocalEntryNotFoundError
        from mlx_lm import load

        logger.info("Loading embedding model: %s", self._model_name)

        # Resolve local path without network / tqdm
        try:
            local_path = snapshot_download(
                repo_id=self._model_name,
                local_files_only=True,
            )
        except (LocalEntryNotFoundError, Exception) as exc:
            raise RuntimeError(
                f"Embedding model '{self._model_name}' not found in local cache.\n"
                f"Download it first:\n"
                f"  uv run python scripts/setup_models.py\n"
                f"Original error: {exc}"
            ) from exc

        model, tokenizer = load(local_path)
        self._pipeline = (model, tokenizer)
        logger.info("Embedding model ready.")

    def encode(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        """Encode texts into L2-normalised float32 vectors.

        Returns shape (N, EMBEDDING_DIM).
        """
        if self._pipeline is None:
            self.load()

        import mlx.core as mx
        model, tokenizer = self._pipeline  # type: ignore[misc]

        all_vecs: list[np.ndarray] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]

            # nomic-embed-text uses a search_document prefix for indexing
            prefixed = [f"search_document: {t}" for t in batch]

            inputs = tokenizer(
                prefixed,
                return_tensors="mlx",
                padding=True,
                truncation=True,
                max_length=512,
            )

            # Mean-pool the last hidden state
            outputs = model(**inputs)
            hidden = outputs.last_hidden_state          # (B, T, D)
            mask = inputs["attention_mask"][..., None]  # (B, T, 1)
            summed = (hidden * mask).sum(axis=1)        # (B, D)
            lengths = mask.sum(axis=1)                  # (B, 1)
            pooled = summed / lengths                   # (B, D)

            mx.eval(pooled)
            vecs = np.array(pooled, dtype=np.float32)

            # L2-normalise for cosine similarity via IndexFlatIP
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1.0, norms)
            vecs = vecs / norms

            all_vecs.append(vecs)
            logger.debug("Encoded batch %d/%d", i // batch_size + 1, -(-len(texts) // batch_size))

        result = np.vstack(all_vecs)
        assert result.shape == (len(texts), EMBEDDING_DIM), (
            f"Expected ({len(texts)}, {EMBEDDING_DIM}), got {result.shape}"
        )
        return result

    @property
    def is_loaded(self) -> bool:
        return self._pipeline is not None
