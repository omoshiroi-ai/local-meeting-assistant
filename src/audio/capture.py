"""AudioCapture — microphone input via sounddevice.

The sounddevice callback runs in a private C thread managed by PortAudio.
Audio frames are placed on a thread-safe queue and consumed by the VAD loop.
"""

import queue
import logging
from typing import Optional

import numpy as np
import sounddevice as sd

from src.config import AUDIO_CHANNELS, AUDIO_CHUNK_SIZE, AUDIO_SAMPLE_RATE

logger = logging.getLogger(__name__)


class AudioCapture:
    """Captures audio from the default input device as float32 mono chunks."""

    def __init__(
        self,
        sample_rate: int = AUDIO_SAMPLE_RATE,
        chunk_size: int = AUDIO_CHUNK_SIZE,
        channels: int = AUDIO_CHANNELS,
    ) -> None:
        self._sample_rate = sample_rate
        self._chunk_size = chunk_size
        self._channels = channels
        self._queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=512)
        self._stream: Optional[sd.InputStream] = None

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def start(self) -> None:
        """Open and start the audio input stream."""
        if self._stream is not None:
            return
        self._stream = sd.InputStream(
            samplerate=self._sample_rate,
            channels=self._channels,
            dtype="float32",
            blocksize=self._chunk_size,
            callback=self._callback,
        )
        self._stream.start()
        logger.info(
            "AudioCapture started: %d Hz, %d ch, block=%d",
            self._sample_rate,
            self._channels,
            self._chunk_size,
        )

    def stop(self) -> None:
        """Stop and close the audio stream, draining the queue."""
        if self._stream is None:
            return
        self._stream.stop()
        self._stream.close()
        self._stream = None
        # Drain any remaining frames so the consumer thread can exit cleanly
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
        logger.info("AudioCapture stopped.")

    def read_chunk(self, timeout: float = 0.1) -> Optional[np.ndarray]:
        """Block until a chunk is available, or return None on timeout."""
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    @property
    def is_running(self) -> bool:
        return self._stream is not None and self._stream.active

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    # ------------------------------------------------------------------ #
    # sounddevice callback (runs in PortAudio C thread)
    # ------------------------------------------------------------------ #

    def _callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info,
        status: sd.CallbackFlags,
    ) -> None:
        if status:
            logger.warning("sounddevice status: %s", status)
        # indata shape: (frames, channels) — take the first (mono) channel
        chunk = indata[:, 0].copy()
        try:
            self._queue.put_nowait(chunk)
        except queue.Full:
            logger.warning("Audio queue full — dropping chunk")
