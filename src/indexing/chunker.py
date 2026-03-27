"""Chunker — sliding-window tokeniser over transcript segments.

Splits a list of TranscriptSegment rows into overlapping text chunks
suitable for embedding and FAISS retrieval.

Each chunk carries the start_ms / end_ms of the segments it spans so
the UI can link retrieved chunks back to timestamps.

Usage::

    from src.indexing.chunker import chunk_segments
    chunks = chunk_segments(segments, meeting_id=42)
    # → list[dict] ready for ChunkRepo.insert_many()
"""

import logging
from dataclasses import dataclass

import tiktoken

from src.config import CHUNK_OVERLAP_TOKENS, CHUNK_TARGET_TOKENS
from src.db.repository import TranscriptSegment

logger = logging.getLogger(__name__)

# cl100k_base is the tokeniser used by GPT-4 / nomic-embed-text
_ENC = tiktoken.get_encoding("cl100k_base")


@dataclass
class Chunk:
    text: str
    start_ms: int
    end_ms: int
    token_count: int


def chunk_segments(
    segments: list[TranscriptSegment],
    meeting_id: int,
    target_tokens: int = CHUNK_TARGET_TOKENS,
    overlap_tokens: int = CHUNK_OVERLAP_TOKENS,
) -> list[dict]:
    """Convert transcript segments into overlapping token-bounded chunks.

    Returns a list of dicts ready for ``ChunkRepo.insert_many()``.
    """
    if not segments:
        return []

    # Tokenise each segment individually so we can track ms offsets
    tokenised: list[tuple[list[int], TranscriptSegment]] = [
        (_ENC.encode(seg.text), seg) for seg in segments
    ]

    chunks: list[Chunk] = []
    i = 0  # index into tokenised list

    while i < len(tokenised):
        buf_tokens: list[int] = []
        buf_start_ms = tokenised[i][1].start_ms
        buf_end_ms = tokenised[i][1].end_ms
        j = i

        # Accumulate segments until we hit the target token count
        while j < len(tokenised):
            toks, seg = tokenised[j]
            if buf_tokens and len(buf_tokens) + len(toks) > target_tokens:
                break
            buf_tokens.extend(toks)
            buf_end_ms = seg.end_ms
            j += 1

        text = _ENC.decode(buf_tokens)
        chunks.append(Chunk(
            text=text,
            start_ms=buf_start_ms,
            end_ms=buf_end_ms,
            token_count=len(buf_tokens),
        ))

        # Advance by (target - overlap) tokens worth of segments
        advance_tokens = max(target_tokens - overlap_tokens, 1)
        consumed = 0
        while i < j and consumed < advance_tokens:
            consumed += len(tokenised[i][0])
            i += 1
        if i == j:  # safety: always make progress
            i = j

    logger.debug(
        "chunked meeting %d: %d segments → %d chunks",
        meeting_id, len(segments), len(chunks),
    )

    return [
        {
            "meeting_id": meeting_id,
            "chunk_index": idx,
            "text": c.text,
            "start_ms": c.start_ms,
            "end_ms": c.end_ms,
            "token_count": c.token_count,
        }
        for idx, c in enumerate(chunks)
    ]
