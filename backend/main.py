"""FastAPI entry point for local meeting assistant backend."""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db import connect, init_db
from backend.routers import sessions, transcription
from backend.routers import chat
from backend.services.transcriber import _ensure_model
from backend.services.llm import LLM_MODEL, LLM_PORT, LLM_SERVER_URL, start_llm_server

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = connect()
    init_db(conn)
    app.state.conn = conn

    logger.info("Checking Whisper model (downloading if needed)…")
    try:
        await asyncio.to_thread(_ensure_model)
        logger.info("Whisper model ready.")
    except Exception as exc:
        logger.error("Failed to prepare Whisper model at startup: %s", exc)

    app.state.llm_url = LLM_SERVER_URL
    llm_proc = None
    try:
        llm_proc = await start_llm_server()
    except Exception as exc:
        logger.error("Failed to start mlx-lm server: %s", exc)

    yield

    if llm_proc is not None and llm_proc.returncode is None:
        llm_proc.terminate()
        try:
            await asyncio.wait_for(llm_proc.wait(), timeout=10)
        except asyncio.TimeoutError:
            llm_proc.kill()
    conn.close()


app = FastAPI(title="Local Meeting Assistant", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions.router)
app.include_router(transcription.router)
app.include_router(chat.router)


@app.get("/api/health")
def health():
    from backend.services import transcriber

    # Check if weights are on disk
    model_cached = False
    try:
        from huggingface_hub import scan_cache_dir
        for repo in scan_cache_dir().repos:
            if repo.repo_id == transcriber._model_id:
                revisions = list(repo.revisions)
                if revisions and (revisions[0].snapshot_path / "weights.safetensors").exists():
                    model_cached = True
                break
    except Exception:
        pass

    model_loaded = transcriber._local_path is not None

    return {
        "status": "ok",
        "model_id": transcriber._model_id,
        "model_cached": model_cached,
        "model_loaded": model_loaded,
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    host = os.environ.get("API_HOST", "127.0.0.1")
    port = int(os.environ.get("API_PORT", "8765"))
    uvicorn.run("backend.main:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    main()
