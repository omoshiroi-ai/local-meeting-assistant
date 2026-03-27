"""Tests for RAG context builder (no MLX / network required)."""

import pytest

from src.db.repository import TranscriptChunk
from src.rag.context_builder import SYSTEM_PROMPT, build_context, build_messages


def _chunk(id: int, text: str, start_ms: int = 0, end_ms: int = 5000) -> TranscriptChunk:
    return TranscriptChunk(
        id=id, meeting_id=1, chunk_index=id,
        text=text, start_ms=start_ms, end_ms=end_ms,
        token_count=len(text.split()),
    )


# ---------------------------------------------------------------------------
# build_context
# ---------------------------------------------------------------------------

def test_empty_chunks_returns_header_only():
    ctx = build_context([])
    assert "Transcript excerpts" in ctx


def test_timestamps_appear_in_context():
    chunk = _chunk(1, "We decided to launch in Q3.", start_ms=65000, end_ms=70000)
    ctx = build_context([chunk])
    assert "01:05" in ctx  # 65 seconds → 01:05


def test_chunk_text_appears_in_context():
    chunk = _chunk(1, "Action item: write the spec.")
    ctx = build_context([chunk])
    assert "Action item: write the spec." in ctx


def test_multiple_chunks_all_included_when_small():
    chunks = [_chunk(i, f"Chunk {i} content.", start_ms=i * 1000, end_ms=(i + 1) * 1000)
              for i in range(5)]
    ctx = build_context(chunks)
    for i in range(5):
        assert f"Chunk {i} content." in ctx


def test_token_budget_excludes_excess_chunks():
    """With a tiny budget, only the first chunk(s) should appear."""
    # Each chunk is ~50 words; budget is very small
    chunks = [_chunk(i, ("word " * 50).strip(), start_ms=i * 5000, end_ms=(i + 1) * 5000)
              for i in range(20)]
    ctx = build_context(chunks)
    # The context must not be astronomically large
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    from src.config import RAG_MAX_CONTEXT_TOKENS
    assert len(enc.encode(ctx)) <= RAG_MAX_CONTEXT_TOKENS


def test_zero_ms_timestamp_formats_as_00_00():
    chunk = _chunk(1, "Opening remarks.", start_ms=0)
    ctx = build_context([chunk])
    assert "[00:00]" in ctx


def test_context_is_string():
    ctx = build_context([_chunk(1, "test")])
    assert isinstance(ctx, str)


# ---------------------------------------------------------------------------
# build_messages
# ---------------------------------------------------------------------------

def test_build_messages_returns_list_of_dicts():
    chunks = [_chunk(1, "Some content.")]
    msgs = build_messages("What was discussed?", chunks)
    assert isinstance(msgs, list)
    assert all(isinstance(m, dict) for m in msgs)


def test_build_messages_has_system_and_user():
    msgs = build_messages("What was decided?", [_chunk(1, "We decided X.")])
    roles = [m["role"] for m in msgs]
    assert "system" in roles
    assert "user" in roles


def test_build_messages_system_prompt_content():
    msgs = build_messages("query", [_chunk(1, "text")])
    system = next(m for m in msgs if m["role"] == "system")
    assert system["content"] == SYSTEM_PROMPT


def test_build_messages_user_contains_query():
    msgs = build_messages("Tell me about the budget.", [_chunk(1, "Budget is $1M.")])
    user = next(m for m in msgs if m["role"] == "user")
    assert "Tell me about the budget." in user["content"]


def test_build_messages_user_contains_chunk_text():
    msgs = build_messages("query", [_chunk(1, "The answer is 42.")])
    user = next(m for m in msgs if m["role"] == "user")
    assert "The answer is 42." in user["content"]
