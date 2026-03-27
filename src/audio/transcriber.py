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

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def load(self) -> None:
        """Download (if needed) and warm up the model. Safe to call multiple times.

        mlx_whisper uses an internal ModelHolder that caches the loaded model
        between transcribe() calls.  We trigger it here by transcribing a tiny
        silent array so that:
          1. snapshot_download() pulls the weights from HuggingFace (first run only)
          2. The model is compiled and resident in memory before real audio arrives
        """
        if self._loaded:
            return
        logger.info("Downloading + loading Whisper model: %s", self._model_name)
        import numpy as np
        import mlx_whisper

        # 0.5 s of silence at 16 kHz — enough to trigger model load, discarded immediately
        dummy = np.zeros(8000, dtype=np.float32)
        mlx_whisper.transcribe(dummy, path_or_hf_repo=self._model_name)

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
            kwargs: dict = {"path_or_hf_repo": self._model_name}
            if language:
                kwargs["language"] = language

            result = mlx_whisper.transcribe(audio, **kwargs)
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
