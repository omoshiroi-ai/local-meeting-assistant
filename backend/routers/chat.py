"""Pass-through proxy to the mlx-lm OpenAI-compatible server."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse

router = APIRouter(tags=["chat"])


@router.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    llm_url: str = request.app.state.llm_url

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
