"""Tests for the transcript chunker (no MLX / network required)."""

import sqlite3

import pytest

from src.db.repository import TranscriptSegment
from src.indexing.chunker import chunk_segments


def _seg(id: int, text: str, start_ms: int = 0, end_ms: int = 1000) -> TranscriptSegment:
    return TranscriptSegment(
        id=id, meeting_id=1, sequence_num=id,
        text=text, start_ms=start_ms, end_ms=end_ms,
    )


# ---------------------------------------------------------------------------
# Basic behaviour
# ---------------------------------------------------------------------------

def test_empty_segments_returns_empty():
    assert chunk_segments([], meeting_id=1) == []


def test_single_segment_produces_one_chunk():
    segs = [_seg(1, "Hello world this is a test.", start_ms=0, end_ms=500)]
    chunks = chunk_segments(segs, meeting_id=1)
    assert len(chunks) == 1
    assert chunks[0]["text"] == "Hello world this is a test."
    assert chunks[0]["meeting_id"] == 1
    assert chunks[0]["chunk_index"] == 0
    assert chunks[0]["start_ms"] == 0
    assert chunks[0]["end_ms"] == 500


def test_chunk_index_is_sequential():
    segs = [_seg(i, f"Segment number {i}. " * 20, start_ms=i * 1000, end_ms=(i + 1) * 1000)
            for i in range(10)]
    chunks = chunk_segments(segs, meeting_id=42, target_tokens=50, overlap_tokens=10)
    for i, c in enumerate(chunks):
        assert c["chunk_index"] == i
        assert c["meeting_id"] == 42


def test_required_keys_present():
    segs = [_seg(1, "Some text here.")]
    chunk = chunk_segments(segs, meeting_id=7)[0]
    assert {"meeting_id", "chunk_index", "text", "start_ms", "end_ms", "token_count"} <= chunk.keys()


def test_token_count_is_positive():
    segs = [_seg(1, "Non-empty text.")]
    chunk = chunk_segments(segs, meeting_id=1)[0]
    assert chunk["token_count"] > 0


# ---------------------------------------------------------------------------
# Chunking logic
# ---------------------------------------------------------------------------

def test_small_content_stays_in_one_chunk():
    """If all segments fit within target_tokens, result is a single chunk."""
    segs = [_seg(i, f"Short {i}.", start_ms=i * 100, end_ms=(i + 1) * 100) for i in range(5)]
    chunks = chunk_segments(segs, meeting_id=1, target_tokens=200, overlap_tokens=20)
    assert len(chunks) == 1


def test_large_content_splits_into_multiple_chunks():
    """Long segments must produce more than one chunk."""
    long_text = "word " * 100  # ~100 tokens per segment
    segs = [_seg(i, long_text, start_ms=i * 5000, end_ms=(i + 1) * 5000) for i in range(5)]
    chunks = chunk_segments(segs, meeting_id=1, target_tokens=80, overlap_tokens=10)
    assert len(chunks) > 1


def test_chunks_respect_target_token_budget():
    """No chunk should massively exceed target_tokens (one segment may push it over by at most 1 seg)."""
    long_text = "token " * 60  # ~60 tokens
    segs = [_seg(i, long_text, start_ms=i * 1000, end_ms=(i + 1) * 1000) for i in range(6)]
    target = 100
    chunks = chunk_segments(segs, meeting_id=1, target_tokens=target, overlap_tokens=20)
    for c in chunks:
        # Each chunk should be at most target + one segment worth of tokens
        assert c["token_count"] <= target + 70, f"chunk too large: {c['token_count']}"


def test_overlap_means_later_chunks_not_empty():
    """With overlap, every chunk should have meaningful content."""
    text = "sentence " * 50
    segs = [_seg(i, text, start_ms=i * 1000, end_ms=(i + 1) * 1000) for i in range(4)]
    chunks = chunk_segments(segs, meeting_id=1, target_tokens=60, overlap_tokens=20)
    for c in chunks:
        assert c["token_count"] > 0
        assert c["text"].strip() != ""


def test_timestamps_span_included_segments():
    """start_ms / end_ms should match the segments actually included in each chunk."""
    segs = [_seg(i, "word " * 30, start_ms=i * 1000, end_ms=(i + 1) * 1000) for i in range(6)]
    chunks = chunk_segments(segs, meeting_id=1, target_tokens=60, overlap_tokens=10)
    # First chunk must start at 0
    assert chunks[0]["start_ms"] == 0
    # end_ms must always be >= start_ms
    for c in chunks:
        assert c["end_ms"] >= c["start_ms"]


def test_always_makes_progress():
    """Chunker must not loop forever even with overlap >= target."""
    segs = [_seg(i, "hello world", start_ms=i * 100, end_ms=(i + 1) * 100) for i in range(10)]
    # Degenerate: overlap equals target
    chunks = chunk_segments(segs, meeting_id=1, target_tokens=10, overlap_tokens=10)
    assert len(chunks) >= 1
