"""Wraps mlx-whisper for on-device transcription."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_model_id: str = "mlx-community/whisper-large-v3-turbo"
_local_path: str | None = None  # resolved after first load


def set_model_id(model_id: str) -> None:
    global _model_id, _local_path
    _model_id = model_id
    _local_path = None


def _ensure_model() -> None:
    """Download model if needed and load weights into MLX (run at startup)."""
    global _local_path
    if _local_path is not None:
        return

    import mlx.core as mx
    from huggingface_hub import snapshot_download
    from mlx_whisper.load_models import load_model
    from mlx_whisper.transcribe import ModelHolder

    logger.info("Resolving Whisper model: %s", _model_id)
    local = snapshot_download(repo_id=_model_id)
    logger.info("Loading weights into MLX from: %s", local)
    ModelHolder.get_model(local, mx.float16)
    _local_path = local
    logger.info("Whisper model ready.")


def _load_audio(audio_path: Path) -> "np.ndarray":
    """Decode any audio file to float32 16 kHz mono via PyAV (no ffmpeg needed)."""
    import av
    import numpy as np

    resampler = av.AudioResampler(format="fltp", layout="mono", rate=16000)
    frames: list[np.ndarray] = []

    with av.open(str(audio_path)) as container:
        for frame in container.decode(audio=0):
            for out_frame in resampler.resample(frame):
                frames.append(out_frame.to_ndarray())

    for out_frame in resampler.resample(None):
        frames.append(out_frame.to_ndarray())

    if not frames:
        raise ValueError(f"No audio frames decoded from {audio_path}")

    return np.concatenate(frames, axis=1).flatten().astype("float32")


def transcribe(audio_path: str | Path, language: str = "en") -> list[dict]:
    """Transcribe an audio file. Returns list of {text, start_sec, end_sec}."""
    import mlx_whisper

    _ensure_model()

    audio_path = Path(audio_path)
    logger.info("Decoding audio: %s", audio_path.name)
    audio = _load_audio(audio_path)

    logger.info("Transcribing %s (%.1fs) with %s", audio_path.name, len(audio) / 16000, _model_id)
    result = mlx_whisper.transcribe(
        audio,
        path_or_hf_repo=_local_path or _model_id,
        language=language,
        verbose=False,
    )

    segments = []
    for seg in result.get("segments") or []:
        text = seg.get("text", "").strip()
        if text:
            segments.append({
                "text": text,
                "start_sec": float(seg.get("start", 0)),
                "end_sec": float(seg.get("end", 0)),
            })

    if not segments:
        text = result.get("text", "").strip()
        if text:
            segments.append({"text": text, "start_sec": 0.0, "end_sec": 0.0})

    logger.info("Transcription done: %d segments", len(segments))
    return segments
