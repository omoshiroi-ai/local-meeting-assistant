"""EnergyVAD — simple RMS-threshold voice activity detector.

Accumulates speech audio into chunks and flushes them when:
  - a period of silence >= ``silence_duration_s`` is detected, OR
  - the accumulated buffer reaches ``max_chunk_s`` seconds (forced flush).

Usage::

    vad = EnergyVAD()
    for raw_chunk in audio_source:
        is_speech, audio, offset_samples = vad.process(raw_chunk)
        if audio is not None:
            transcriber.submit(audio, offset_samples)
"""

import logging
from dataclasses import dataclass, field

import numpy as np

from src.config import (
    AUDIO_SAMPLE_RATE,
    VAD_MAX_CHUNK_S,
    VAD_SILENCE_DURATION_S,
    VAD_SILENCE_THRESHOLD,
)

logger = logging.getLogger(__name__)


@dataclass
class VADResult:
    """Returned by EnergyVAD.process() every call."""

    is_speech: bool            # True if this chunk was classified as speech
    audio: np.ndarray | None   # Non-None when a complete speech segment is ready
    offset_samples: int        # Sample index of the start of `audio` in the stream


class EnergyVAD:
    """Energy-based voice activity detector."""

    def __init__(
        self,
        threshold: float = VAD_SILENCE_THRESHOLD,
        silence_duration_s: float = VAD_SILENCE_DURATION_S,
        max_chunk_s: float = VAD_MAX_CHUNK_S,
        sample_rate: int = AUDIO_SAMPLE_RATE,
    ) -> None:
        self._threshold = threshold
        self._silence_samples_needed = int(silence_duration_s * sample_rate)
        self._max_chunk_samples = int(max_chunk_s * sample_rate)
        self._sample_rate = sample_rate

        self._buffer: list[np.ndarray] = []
        self._silence_samples: int = 0
        self._is_speaking: bool = False
        self._total_samples: int = 0        # samples seen since last reset()
        self._segment_start: int = 0        # stream offset where current buffer began

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def process(self, chunk: np.ndarray) -> VADResult:
        """Process one audio chunk.  Returns a VADResult every call.

        ``result.audio`` is non-None when a complete speech segment is
        ready for transcription.
        """
        rms = float(np.sqrt(np.mean(chunk.astype(np.float64) ** 2)))
        is_speech = rms > self._threshold

        self._total_samples += len(chunk)

        if is_speech:
            if not self._is_speaking:
                # Transition: silence → speech
                self._is_speaking = True
                self._segment_start = self._total_samples - len(chunk)
                self._silence_samples = 0
            self._buffer.append(chunk.copy())
            self._silence_samples = 0
        else:
            if self._is_speaking:
                # Still accumulating trailing silence inside a speech segment
                self._buffer.append(chunk.copy())
                self._silence_samples += len(chunk)

        # Decide whether to flush
        flush_audio, flush_offset = self._maybe_flush()
        return VADResult(is_speech=is_speech, audio=flush_audio, offset_samples=flush_offset)

    def reset(self) -> None:
        """Discard accumulated state (call when recording stops)."""
        self._buffer.clear()
        self._silence_samples = 0
        self._is_speaking = False
        self._total_samples = 0
        self._segment_start = 0

    def flush(self) -> VADResult:
        """Force-flush any remaining buffered audio (call at end of recording)."""
        audio, offset = self._do_flush()
        return VADResult(is_speech=False, audio=audio, offset_samples=offset)

    # ------------------------------------------------------------------ #
    # Private
    # ------------------------------------------------------------------ #

    def _maybe_flush(self) -> tuple[np.ndarray | None, int]:
        if not self._buffer:
            return None, 0

        buffer_samples = sum(len(c) for c in self._buffer)
        silence_ended = self._silence_samples >= self._silence_samples_needed
        max_reached = buffer_samples >= self._max_chunk_samples

        if silence_ended or max_reached:
            reason = "silence" if silence_ended else "max-length"
            duration_s = buffer_samples / self._sample_rate
            logger.debug("VAD flush (%s): %.1fs chunk", reason, duration_s)
            return self._do_flush()

        return None, 0

    def _do_flush(self) -> tuple[np.ndarray | None, int]:
        if not self._buffer:
            return None, 0
        audio = np.concatenate(self._buffer)
        offset = self._segment_start
        self._buffer.clear()
        self._silence_samples = 0
        self._is_speaking = False
        self._segment_start = self._total_samples
        return audio, offset
