"""Proxy to the mlx-lm OpenAI-compatible server with RAG context injection."""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

_RAG_SYSTEM_PROMPT = (
    "You are a helpful meeting assistant. "
    "Answer questions using the transcript excerpts provided. "
    "If the excerpts don't contain relevant information, say so clearly."
)


def _build_messages_with_context(messages: list[dict], contexts: list[str]) -> list[dict]:
    context_block = "\n\n---\n\n".join(contexts)
    rag_system = {
        "role": "system",
        "content": f"{_RAG_SYSTEM_PROMPT}\n\n## Relevant transcript excerpts:\n\n{context_block}",
    }
    # Replace existing system message if present, otherwise prepend
    if messages and messages[0]["role"] == "system":
        return [rag_system] + messages[1:]
    return [rag_system] + messages


@router.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    llm_url: str = request.app.state.llm_url
    messages: list[dict] = body.get("messages", [])

    # Retrieve relevant transcript context for the last user message
    user_query = next(
        (m["content"] for m in reversed(messages) if m.get("role") == "user"),
        None,
    )
    if user_query:
        try:
            from backend.services.rag import retrieve
            contexts = retrieve(user_query, top_k=5)
            if contexts:
                messages = _build_messages_with_context(messages, contexts)
                body = {**body, "messages": messages}
        except Exception:
            logger.exception("RAG retrieval failed, proceeding without context")

    if body.get("stream", False):
        async def generate():
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"{llm_url}/v1/chat/completions",
                    json=body,
                    timeout=None,
                ) as resp:
                    async for chunk in resp.aiter_bytes():
                        yield chunk

        return StreamingResponse(generate(), media_type="text/event-stream")

    async with httpx.AsyncClient(timeout=None) as client:
        resp = await client.post(f"{llm_url}/v1/chat/completions", json=body)

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type="application/json",
    )
