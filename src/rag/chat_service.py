"""Shared RAG chat pipeline (retrieval + LLM stream). Used by Textual UI and HTTP API."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass

from src.db.llm_settings import get_effective_max_new_tokens, get_effective_model_id
from src.db.repository import TranscriptChunk
from src.rag.context_builder import build_messages
from src.rag.llm import LLM
from src.rag.retriever import Retriever

logger = logging.getLogger(__name__)


@dataclass
class RAGStream:
    """Result of preparing a streamed answer."""

    chunk_ids: list[int]
    chunks: list[TranscriptChunk]
    token_stream: Iterator[str]


def prepare_rag_stream(
    conn: sqlite3.Connection,
    meeting_id: int,
    query: str,
) -> RAGStream | None:
    """Load retriever + LLM and return chunk ids plus token iterator. Returns None if no chunks."""
    retriever = Retriever(conn)
    retriever.load()
    chunks = retriever.retrieve(query, meeting_id=meeting_id)

    if not chunks:
        return None

    messages = build_messages(query, chunks)
    chunk_ids = [c.id for c in chunks]

    model_id = get_effective_model_id(conn)
    max_tok = get_effective_max_new_tokens(conn)
    llm = LLM(model_name=model_id)
    llm.load()

    return RAGStream(
        chunk_ids=chunk_ids,
        chunks=chunks,
        token_stream=llm.stream(messages, max_tokens=max_tok),
    )
