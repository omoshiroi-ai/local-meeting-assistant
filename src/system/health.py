"""System health checks (mic + cached models). Plain strings — safe for JSON APIs and TUI."""

from __future__ import annotations

import sqlite3
from typing import Any


def check_microphone() -> tuple[bool, str]:
    """Open the mic briefly and verify non-silent audio."""
    try:
        import time

        import numpy as np
        import sounddevice as sd

        chunks: list[np.ndarray] = []

        def _cb(indata, frames, t, status):
            chunks.append(indata[:, 0].copy())

        with sd.InputStream(
            samplerate=16000,
            channels=1,
            dtype="float32",
            blocksize=1024,
            callback=_cb,
        ):
            time.sleep(0.5)

        if not chunks:
            return False, "No audio received from device"

        max_rms = max(float(np.sqrt(np.mean(c**2))) for c in chunks)

        if max_rms == 0.0:
            return (
                False,
                "Mic returns silence — grant microphone access in "
                "System Settings → Privacy & Security → Microphone",
            )

        device = sd.query_devices(kind="input")
        name = device.get("name", "unknown") if isinstance(device, dict) else "unknown"
        return True, f"{name} (RMS {max_rms:.4f})"

    except Exception as exc:
        return False, f"Error: {exc}"


def _check_hf_model(repo_id: str, setup_flag: str = "") -> tuple[bool, str]:
    try:
        from pathlib import Path

        from huggingface_hub import snapshot_download
        from huggingface_hub.utils import LocalEntryNotFoundError

        short = repo_id.split("/")[-1]

        if Path(repo_id).exists():
            return True, f"Ready ({short})"

        try:
            snapshot_download(repo_id=repo_id, local_files_only=True)
            return True, f"Ready ({short})"
        except (LocalEntryNotFoundError, Exception):
            cmd = f"setup_models.py {setup_flag}".strip()
            return False, f"Missing {short} — run: uv run python scripts/{cmd}"

    except Exception as exc:
        return False, f"Error: {exc}"


def check_whisper_model() -> tuple[bool, str]:
    from src.config import WHISPER_MODEL

    return _check_hf_model(WHISPER_MODEL, "--whisper-only")


def check_embedding_model() -> tuple[bool, str]:
    from src.config import EMBEDDING_MODEL

    return _check_hf_model(EMBEDDING_MODEL)


def check_llm_model(repo_id: str | None = None) -> tuple[bool, str]:
    from src.config import LLM_MODEL

    return _check_hf_model(repo_id or LLM_MODEL)


def health_snapshot(conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    """Aggregate status for API and UI.

    When ``conn`` is provided, the LLM cache check uses the DB-configured model id
    (if any) instead of only ``LLM_MODEL`` from the environment.
    """
    from src.config import LLM_MODEL
    from src.db.llm_settings import get_effective_model_id

    mic_ok, mic_msg = check_microphone()
    whisper_ok, whisper_msg = check_whisper_model()
    embed_ok, embed_msg = check_embedding_model()
    llm_repo = get_effective_model_id(conn)
    llm_ok, llm_msg = check_llm_model(llm_repo)
    return {
        "microphone": {"ok": mic_ok, "message": mic_msg},
        "whisper": {"ok": whisper_ok, "message": whisper_msg},
        "embedding": {"ok": embed_ok, "message": embed_msg},
        "llm": {"ok": llm_ok, "message": llm_msg},
    }
