"""ChromaDB-backed RAG service using mlx-embeddings for local inference."""

from __future__ import annotations

import logging
import os
from pathlib import Path

# ChromaDB's opentelemetry dependency uses old protobuf-generated files that are
# incompatible with protobuf >=4 in C-extension mode. Pure-Python mode works fine.
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data"
CHROMA_PATH = DATA_DIR / "chromadb"
COLLECTION_NAME = "meeting_transcripts"
EMBED_MODEL = "mlx-community/all-MiniLM-L6-v2-4bit"

_model = None
_tokenizer = None
_collection = None


def _get_embedding_model():
    global _model, _tokenizer
    if _model is None:
        from mlx_embeddings.utils import load
        logger.info("Loading embedding model: %s", EMBED_MODEL)
        _model, _tokenizer = load(EMBED_MODEL)
        logger.info("Embedding model ready.")
    return _model, _tokenizer


def _embed(texts: list[str]) -> list[list[float]]:
    import mlx.core as mx

    model, tokenizer = _get_embedding_model()
    inputs = tokenizer.batch_encode_plus(
        texts,
        return_tensors="mlx",
        padding=True,
        truncation=True,
        max_length=512,
    )
    outputs = model(inputs["input_ids"], attention_mask=inputs["attention_mask"])
    embeddings = outputs.text_embeds
    mx.eval(embeddings)
    return embeddings.tolist()


def get_collection():
    global _collection
    if _collection is None:
        import chromadb

        CHROMA_PATH.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("ChromaDB collection ready: %s", COLLECTION_NAME)
    return _collection


def _chunk_segments(
    segments: list[dict], max_chars: int = 600, overlap_chars: int = 100
) -> list[dict]:
    """
    Group consecutive Whisper segments into larger chunks.
    Whisper segments are often only a few seconds — short chunks produce poor embeddings.
    """
    chunks: list[dict] = []
    current_text = ""
    current_start = 0.0
    current_end = 0.0
    last_overlap = ""

    for seg in segments:
        text = seg["text"].strip()
        if not text:
            continue

        if not current_text:
            current_text = (last_overlap + " " + text).strip() if last_overlap else text
            current_start = seg["start_sec"]
        else:
            current_text += " " + text
        current_end = seg["end_sec"]

        if len(current_text) >= max_chars:
            chunks.append(
                {
                    "text": current_text.strip(),
                    "start_sec": current_start,
                    "end_sec": current_end,
                }
            )
            last_overlap = current_text[-overlap_chars:].strip()
            current_text = ""

    if current_text.strip():
        chunks.append(
            {
                "text": current_text.strip(),
                "start_sec": current_start,
                "end_sec": current_end,
            }
        )

    return chunks


def ingest_session(session_id: int, session_title: str, segments: list[dict]) -> int:
    """
    Chunk segments, embed, and upsert into ChromaDB.
    Idempotent — deletes existing chunks for the session before re-indexing.
    Returns the number of chunks stored.
    """
    if not segments:
        logger.warning("No segments to ingest for session %d", session_id)
        return 0

    collection = get_collection()

    # Delete existing chunks so re-indexing is safe
    collection.delete(where={"session_id": session_id})

    chunks = _chunk_segments(segments)
    if not chunks:
        return 0

    texts = [c["text"] for c in chunks]
    embeddings = _embed(texts)

    ids = [f"session_{session_id}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "session_id": session_id,
            "session_title": session_title,
            "start_sec": c["start_sec"],
            "end_sec": c["end_sec"],
            "chunk_index": i,
        }
        for i, c in enumerate(chunks)
    ]

    collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
    logger.info("Indexed %d chunks for session %d (%s)", len(chunks), session_id, session_title)
    return len(chunks)


def retrieve(query: str, session_id: int | None = None, top_k: int = 5) -> list[str]:
    """
    Semantic search over meeting transcripts.
    Optionally scoped to a single session.
    Returns formatted context strings ready to inject into a prompt.
    """
    collection = get_collection()

    if collection.count() == 0:
        return []

    query_embedding = _embed([query])[0]
    where = {"session_id": session_id} if session_id is not None else None

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        where=where,
        include=["documents", "metadatas"],
    )

    contexts: list[str] = []
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]

    for doc, meta in zip(docs, metas):
        title = meta.get("session_title", "Unknown")
        start = float(meta.get("start_sec", 0))
        end = float(meta.get("end_sec", 0))
        ts = f"{int(start // 60):02d}:{int(start % 60):02d}–{int(end // 60):02d}:{int(end % 60):02d}"
        contexts.append(f"[Meeting: {title} | {ts}]\n{doc}")

    return contexts


def delete_session(session_id: int) -> None:
    """Remove all ChromaDB chunks for a session."""
    collection = get_collection()
    collection.delete(where={"session_id": session_id})
    logger.info("Deleted ChromaDB chunks for session %d", session_id)


def get_stats() -> dict:
    collection = get_collection()
    return {"total_chunks": collection.count(), "collection": COLLECTION_NAME}
