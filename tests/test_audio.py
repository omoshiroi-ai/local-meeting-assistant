"""Unit tests for VAD and Transcriber (no real microphone or MLX required)."""

import numpy as np
import pytest

from src.audio.vad import EnergyVAD


# Helpers to generate synthetic audio at 16 kHz
RATE = 16000


def silence(duration_s: float) -> np.ndarray:
    return np.zeros(int(duration_s * RATE), dtype=np.float32)


def speech(duration_s: float, amplitude: float = 0.5) -> np.ndarray:
    """Sine wave loud enough to be above the default VAD threshold."""
    n = int(duration_s * RATE)
    t = np.linspace(0, duration_s, n, dtype=np.float32)
    return (amplitude * np.sin(2 * np.pi * 440 * t)).astype(np.float32)


CHUNK = 1024  # samples per chunk, matching AudioCapture default


def feed(vad: EnergyVAD, audio: np.ndarray) -> list:
    """Feed audio chunk-by-chunk through the VAD; collect non-None results."""
    results = []
    for i in range(0, len(audio), CHUNK):
        chunk = audio[i : i + CHUNK]
        if len(chunk) == 0:
            continue
        r = vad.process(chunk)
        if r.audio is not None:
            results.append(r)
    return results


# ---------------------------------------------------------------------------
# EnergyVAD — silence detection
# ---------------------------------------------------------------------------


class TestEnergyVAD:
    def test_silence_produces_no_output(self):
        vad = EnergyVAD(sample_rate=RATE)
        results = feed(vad, silence(2.0))
        assert results == [], "Pure silence should never flush"

    def test_speech_followed_by_silence_flushes(self):
        vad = EnergyVAD(silence_duration_s=0.5, sample_rate=RATE)
        audio = np.concatenate([speech(1.0), silence(1.0)])
        results = feed(vad, audio)
        assert len(results) == 1
        result = results[0]
        assert result.audio is not None
        # The flushed audio should be at least 1 second (speech) long
        assert len(result.audio) >= RATE

    def test_offset_is_nonzero_after_leading_silence(self):
        """Speech that starts after initial silence should have a non-zero offset."""
        vad = EnergyVAD(silence_duration_s=0.3, sample_rate=RATE)
        # 0.5 s silence, then 1 s speech, then 0.5 s silence (flush trigger)
        audio = np.concatenate([silence(0.5), speech(1.0), silence(0.5)])
        results = feed(vad, audio)
        assert len(results) == 1
        # offset should be approximately 0.5 s * RATE samples
        assert results[0].offset_samples >= int(0.4 * RATE)

    def test_max_chunk_forces_flush(self):
        """Continuous speech exceeding max_chunk_s must be flushed mid-stream."""
        vad = EnergyVAD(max_chunk_s=1.0, silence_duration_s=10.0, sample_rate=RATE)
        # Feed 3 seconds of unbroken speech — should flush at least twice
        results = feed(vad, speech(3.0))
        assert len(results) >= 2

    def test_multiple_speech_segments_flush_separately(self):
        vad = EnergyVAD(silence_duration_s=0.3, sample_rate=RATE)
        # Two speech segments separated by enough silence
        audio = np.concatenate([
            speech(0.5),
            silence(1.0),
            speech(0.5),
            silence(1.0),
        ])
        results = feed(vad, audio)
        assert len(results) == 2

    def test_reset_clears_state(self):
        vad = EnergyVAD(silence_duration_s=0.3, sample_rate=RATE)
        # Accumulate some speech
        feed(vad, speech(0.5))
        vad.reset()
        # After reset, silence should not trigger a flush
        results = feed(vad, silence(2.0))
        assert results == []

    def test_flush_returns_remaining_audio(self):
        vad = EnergyVAD(silence_duration_s=5.0, sample_rate=RATE)
        # Feed speech that won't auto-flush (silence threshold not reached)
        feed(vad, speech(0.5))
        final = vad.flush()
        assert final.audio is not None
        assert len(final.audio) > 0

    def test_flush_on_empty_buffer_returns_none(self):
        vad = EnergyVAD(sample_rate=RATE)
        result = vad.flush()
        assert result.audio is None

    def test_is_speech_flag(self):
        """VADResult.is_speech should reflect current chunk classification."""
        vad = EnergyVAD(sample_rate=RATE)
        loud_chunk = speech(CHUNK / RATE, amplitude=0.8)
        quiet_chunk = silence(CHUNK / RATE)
        assert vad.process(loud_chunk).is_speech is True
        assert vad.process(quiet_chunk).is_speech is False

    def test_amplitude_below_threshold_is_silence(self):
        """Very quiet audio (below threshold) should not be treated as speech."""
        vad = EnergyVAD(threshold=0.1, sample_rate=RATE)
        quiet_speech = speech(1.0, amplitude=0.01)
        results = feed(vad, quiet_speech)
        assert results == []


# ---------------------------------------------------------------------------
# Transcriber — interface only (no actual MLX inference)
# ---------------------------------------------------------------------------


class TestTranscriberInterface:
    def test_not_loaded_initially(self):
        from src.audio.transcriber import Transcriber

        t = Transcriber("mlx-community/whisper-tiny")
        assert t.is_loaded is False

    def test_model_name_stored(self):
        from src.audio.transcriber import Transcriber

        t = Transcriber("mlx-community/whisper-small.en")
        assert t.model_name == "mlx-community/whisper-small.en"

    def test_transcription_result_dataclass(self):
        from src.audio.transcriber import TranscriptionResult

        r = TranscriptionResult(text="hello world", offset_ms=1000, duration_ms=2000)
        assert r.text == "hello world"
        assert r.offset_ms == 1000
        assert r.duration_ms == 2000
