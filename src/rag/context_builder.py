"""ContextBuilder — assemble retrieved chunks into an LLM prompt.

Formats chunks as timestamped excerpts and enforces a token budget
so the assembled context never exceeds RAG_MAX_CONTEXT_TOKENS.
"""

import logging

import tiktoken

from src.config import RAG_MAX_CONTEXT_TOKENS
from src.db.repository import TranscriptChunk

logger = logging.getLogger(__name__)

_ENC = tiktoken.get_encoding("cl100k_base")

SYSTEM_PROMPT = """\
You are a meeting assistant. Answer questions about the user's meetings using \
ONLY the provided transcript excerpts. If the answer is not in the excerpts, \
say so clearly. Be concise and cite the timestamp when referencing specific content.\
"""


def build_context(chunks: list[TranscriptChunk]) -> str:
    """Format chunks into a context block for the LLM prompt.

    Respects RAG_MAX_CONTEXT_TOKENS budget. Truncates least-relevant
    chunks (assumed to be at the end of the list) first.
    """
    lines: list[str] = ["Transcript excerpts:\n"]
    budget = RAG_MAX_CONTEXT_TOKENS - len(_ENC.encode(SYSTEM_PROMPT)) - 50  # headroom

    used = 0
    included = 0
    for chunk in chunks:
        mins, secs = divmod(chunk.start_ms // 1000, 60)
        ts = f"{mins:02d}:{secs:02d}"
        line = f"[{ts}] {chunk.text}\n"
        toks = len(_ENC.encode(line))
        if used + toks > budget:
            break
        lines.append(line)
        used += toks
        included += 1

    if included < len(chunks):
        logger.debug("Context budget: included %d/%d chunks", included, len(chunks))

    return "".join(lines)


def build_messages(query: str, chunks: list[TranscriptChunk]) -> list[dict]:
    """Build the messages list for mlx_lm.generate()."""
    context = build_context(chunks)
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"{context}\n\nQuestion: {query}"},
    ]
