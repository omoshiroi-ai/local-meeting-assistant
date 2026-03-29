"""MLX-LM server subprocess manager."""

from __future__ import annotations

import asyncio
import logging
import os
import sys

import httpx

logger = logging.getLogger(__name__)

LLM_MODEL = os.environ.get("LLM_MODEL", "mlx-community/Qwen2.5-7B-Instruct-4bit")
LLM_PORT = int(os.environ.get("LLM_PORT", "8080"))
LLM_SERVER_URL = f"http://127.0.0.1:{LLM_PORT}"

_HEALTH_POLL_INTERVAL = 2.0  # seconds between health checks
_HEALTH_TIMEOUT = 600  # seconds to wait for server to become healthy


async def start_llm_server(
    model: str = LLM_MODEL,
    port: int = LLM_PORT,
) -> asyncio.subprocess.Process:
    """Start mlx-lm server as a subprocess and wait until healthy.

    Blocks until the server responds to /health or raises RuntimeError on timeout.
    """
    logger.info("Starting mlx-lm server: model=%s port=%d", model, port)
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "mlx_lm.server",
        "--model", model,
        "--port", str(port),
    )

    health_url = f"http://127.0.0.1:{port}/health"
    elapsed = 0.0
    async with httpx.AsyncClient() as client:
        while elapsed < _HEALTH_TIMEOUT:
            await asyncio.sleep(_HEALTH_POLL_INTERVAL)
            elapsed += _HEALTH_POLL_INTERVAL

            if proc.returncode is not None:
                raise RuntimeError(
                    f"mlx-lm server exited unexpectedly (code {proc.returncode})"
                )

            try:
                r = await client.get(health_url, timeout=2.0)
                if r.status_code == 200:
                    logger.info("mlx-lm server ready (%.0fs elapsed)", elapsed)
                    return proc
            except (httpx.ConnectError, httpx.TimeoutException):
                if int(elapsed) % 30 == 0:
                    logger.info("Still waiting for mlx-lm server… (%.0fs)", elapsed)

    proc.terminate()
    raise RuntimeError(f"mlx-lm server did not become healthy within {_HEALTH_TIMEOUT}s")
