"""Download and cache all required MLX models.

Run once before first use:
    uv run python scripts/setup_models.py

Models downloaded:
    - mlx-community/whisper-large-v3-turbo  (~800 MB)  STT
    - mlx-community/nomic-embed-text-v1.5   (~275 MB)  Embeddings
    - mlx-community/Qwen2.5-7B-Instruct-4bit (~4.5 GB) Chat LLM

Pass --whisper-only to download just the STT model.
"""

import argparse
import sys
import time


def download_whisper(model_name: str) -> None:
    print(f"\n[1/3] Whisper STT — {model_name}")
    print("      Downloading… this may take several minutes.")
    t0 = time.monotonic()
    # Use snapshot_download directly — safe on the main thread (tqdm works here)
    from huggingface_hub import snapshot_download
    import mlx.core as mx
    from mlx_whisper.load_models import load_model
    from mlx_whisper.transcribe import ModelHolder

    local_path = snapshot_download(repo_id=model_name)
    print("      Weights downloaded. Loading into MLX…")
    ModelHolder.get_model(local_path, mx.float16)
    elapsed = time.monotonic() - t0
    print(f"      ✓ Done in {elapsed:.0f}s")


def download_embeddings(model_name: str) -> None:
    print(f"\n[2/3] Embeddings — {model_name}")
    print("      Downloading…")
    t0 = time.monotonic()
    from huggingface_hub import snapshot_download
    local_path = snapshot_download(repo_id=model_name)
    print("      Weights downloaded. Loading into MLX…")
    from mlx_lm import load
    load(local_path)
    elapsed = time.monotonic() - t0
    print(f"      ✓ Done in {elapsed:.0f}s")


def download_llm(model_name: str) -> None:
    print(f"\n[3/3] Chat LLM — {model_name}")
    print("      Downloading… (~4.5 GB, largest download)")
    t0 = time.monotonic()
    from huggingface_hub import snapshot_download
    snapshot_download(repo_id=model_name)
    elapsed = time.monotonic() - t0
    print(f"      ✓ Done in {elapsed:.0f}s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download MLX models for local-meeting-assistant.")
    parser.add_argument(
        "--whisper-only",
        action="store_true",
        help="Download only the Whisper STT model (fastest, needed to transcribe).",
    )
    parser.add_argument(
        "--whisper-model",
        default=None,
        help="Override the Whisper model ID (default: from src/config.py).",
    )
    args = parser.parse_args()

    from src.config import EMBEDDING_MODEL, LLM_MODEL, WHISPER_MODEL

    whisper_model = args.whisper_model or WHISPER_MODEL

    print("=" * 60)
    print("  Local Meeting Assistant — Model Setup")
    print("=" * 60)

    total_start = time.monotonic()

    try:
        download_whisper(whisper_model)
    except Exception as e:
        print(f"\n  ERROR downloading Whisper: {e}", file=sys.stderr)
        sys.exit(1)

    if not args.whisper_only:
        try:
            download_embeddings(EMBEDDING_MODEL)
        except Exception as e:
            print(f"\n  WARNING: Embeddings download failed: {e}", file=sys.stderr)
            print("  (Needed for Phase 4 indexing — you can retry later)")

        try:
            download_llm(LLM_MODEL)
        except Exception as e:
            print(f"\n  WARNING: LLM download failed: {e}", file=sys.stderr)
            print("  (Needed for Phase 5 chat — you can retry later)")

    total = time.monotonic() - total_start
    print(f"\n{'=' * 60}")
    print(f"  Setup complete in {total:.0f}s.")
    print(f"  Run the app:  uv run meeting-assistant")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
