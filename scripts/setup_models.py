"""Download and warm up all required models before running the backend.

Run once before first use:
    uv run python scripts/setup_models.py

Models:
    - mlx-community/whisper-large-v3-turbo  (~800 MB)  STT  [required]
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

WHISPER_MODEL = "mlx-community/whisper-large-v3-turbo"


def _get_snapshot(model_id: str) -> Path | None:
    from huggingface_hub import scan_cache_dir
    try:
        for repo in scan_cache_dir().repos:
            if repo.repo_id == model_id:
                revisions = list(repo.revisions)
                if revisions:
                    return revisions[0].snapshot_path
    except Exception:
        pass
    return None


def setup_whisper(model_id: str) -> bool:
    print(f"\n[ Whisper STT ]")
    print(f"  Model : {model_id}")
    t0 = time.monotonic()

    # Step 1 — download weights
    snapshot = _get_snapshot(model_id)
    if snapshot and (snapshot / "weights.safetensors").exists():
        print(f"  Weights: already cached")
        print(f"           {snapshot}")
    else:
        print("  Weights: downloading (~800 MB)…")
        try:
            from huggingface_hub import snapshot_download
            local = snapshot_download(repo_id=model_id)
            print(f"  Weights: downloaded to {local} ({time.monotonic() - t0:.0f}s)")
        except Exception as e:
            print(f"  Weights: FAILED — {e}", file=sys.stderr)
            return False

    # Step 2 — warm up: run a silent transcription to load weights into MLX
    print("  Loading into MLX… ", end="", flush=True)
    t1 = time.monotonic()
    try:
        import numpy as np
        import mlx_whisper
        # 1-second silence as float32 array — triggers model load without ffmpeg
        silence = np.zeros(16000, dtype=np.float32)
        mlx_whisper.transcribe(silence, path_or_hf_repo=model_id, verbose=False)
        print(f"OK ({time.monotonic() - t1:.0f}s)")
    except Exception as e:
        print(f"FAILED\n  Error: {e}", file=sys.stderr)
        return False

    print(f"  Total : {time.monotonic() - t0:.0f}s")
    return True


def check_whisper(model_id: str) -> None:
    snapshot = _get_snapshot(model_id)
    if snapshot and (snapshot / "weights.safetensors").exists():
        print(f"  [OK]  {model_id}")
        print(f"        {snapshot}")
    else:
        print(f"  [--]  {model_id}  (not downloaded)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download and verify all models for local-meeting-assistant.",
    )
    parser.add_argument(
        "--whisper-model",
        default=WHISPER_MODEL,
        metavar="HF_REPO",
        help=f"Override Whisper model (default: {WHISPER_MODEL})",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Report cache status without downloading.",
    )
    args = parser.parse_args()

    width = 60
    print("=" * width)
    print("  Local Meeting Assistant — Model Setup")
    print("=" * width)

    if args.check_only:
        print()
        check_whisper(args.whisper_model)
        print()
        return

    total_start = time.monotonic()
    ok = setup_whisper(args.whisper_model)

    print(f"\n{'=' * width}")
    if ok:
        print(f"  Done. ({time.monotonic() - total_start:.0f}s)")
        print(f"  Start backend:  uv run python -m backend.main")
    else:
        print(f"  Setup failed. Check errors above.")
        sys.exit(1)
    print(f"{'=' * width}\n")


if __name__ == "__main__":
    main()
