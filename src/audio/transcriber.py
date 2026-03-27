"""Transcriber — synchronous MLX Whisper wrapper.

Designed to be called from a dedicated worker thread.  The model is loaded
lazily on the first call to ``transcribe()``, so the caller can show a
"loading" indicator before the first result arrives.

Usage (from a thread worker)::

    t = Transcriber("mlx-community/whisper-large-v3-turbo")
    t.load()          # blocks ~5-10 s on first download
    text = t.transcribe(audio_float32_16khz)
"""

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from src.config import WHISPER_MODEL

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    text: str
    offset_ms: int          # millisecond offset in the meeting recording
    duration_ms: int        # approximate duration of the transcribed audio


class Transcriber:
    """Wraps mlx_whisper.transcribe with lazy model loading."""

    def __init__(self, model_name: str = WHISPER_MODEL) -> None:
        self._model_name = model_name
        self._loaded = False
        self._local_path: str | None = None  # resolved after load()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def load(self) -> None:
        """Resolve the cached model path and load weights into MLX.

        Must be called before transcribe().  Safe to call multiple times.

        We intentionally use local_files_only=True here to avoid tqdm creating
        a multiprocessing.RLock inside Textual's thread-pool executor, which
        fails with a resource-tracker error.  Run scripts/setup_models.py first
        to download the weights.
        """
        if self._loaded:
            return

        from huggingface_hub import snapshot_download
        from huggingface_hub.utils import LocalEntryNotFoundError
        import mlx.core as mx
        from mlx_whisper.load_models import load_model
        from mlx_whisper.transcribe import ModelHolder

        logger.info("Resolving Whisper model path: %s", self._model_name)

        # Resolve local path — no network, no tqdm, no multiprocessing locks
        model_dir = Path(self._model_name)
        if model_dir.exists():
            local_path = str(model_dir)
        else:
            try:
                local_path = snapshot_download(
                    repo_id=self._model_name,
                    local_files_only=True,
                )
            except (LocalEntryNotFoundError, Exception) as exc:
                raise RuntimeError(
                    f"Whisper model '{self._model_name}' not found in local cache.\n"
                    f"Download it first:\n"
                    f"  uv run python scripts/setup_models.py --whisper-only\n"
                    f"Original error: {exc}"
                ) from exc

        logger.info("Loading Whisper weights from: %s", local_path)
        ModelHolder.get_model(local_path, mx.float16)
        self._local_path = local_path
        self._loaded = True
        logger.info("Whisper model ready.")

    def transcribe(
        self,
        audio: np.ndarray,
        offset_ms: int = 0,
        language: str | None = "en",
    ) -> TranscriptionResult | None:
        """Transcribe a float32 mono 16 kHz numpy array.

        Returns None if no speech was detected or the result is empty.
        Blocks the calling thread for the duration of inference.
        """
        if not self._loaded:
            self.load()

        import mlx_whisper

        duration_ms = int(len(audio) / 16000 * 1000)

        try:
            # Use the resolved local path so ModelHolder hits the cache every time
            path = self._local_path or self._model_name
            kwargs: dict = {"path_or_hf_repo": path}
            if language:
                kwargs["language"] = language

            result = mlx_whisper.transcribe(audio, verbose=False, **kwargs)
        except Exception:
            logger.exception("Whisper transcription failed")
            return None

        text = result.get("text", "").strip()
        if not text:
            return None

        logger.debug("Transcribed (%dms offset, %dms): %r", offset_ms, duration_ms, text[:60])
        return TranscriptionResult(text=text, offset_ms=offset_ms, duration_ms=duration_ms)

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def model_name(self) -> str:
        return self._model_name
