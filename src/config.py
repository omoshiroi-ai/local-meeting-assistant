"""App-wide configuration: paths, model IDs, and tunable constants."""

import os
from pathlib import Path

# --- Paths ---

ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = Path(os.environ.get("MEETING_DATA_DIR", ROOT_DIR / "data"))
DB_PATH = DATA_DIR / "meetings.db"
FAISS_DIR = DATA_DIR / "faiss"
FAISS_INDEX_PATH = FAISS_DIR / "meetings.index"
FAISS_META_PATH = FAISS_DIR / "meetings.meta.json"

# --- MLX Model IDs (HuggingFace repo IDs) ---

WHISPER_MODEL = os.environ.get(
    "WHISPER_MODEL", "mlx-community/whisper-large-v3-turbo"
)
EMBEDDING_MODEL = os.environ.get(
    "EMBEDDING_MODEL", "mlx-community/nomic-embed-text-v1.5"
)
LLM_MODEL = os.environ.get(
    "LLM_MODEL", "mlx-community/Qwen2.5-7B-Instruct-4bit"
)

# --- Audio ---

AUDIO_SAMPLE_RATE = 16000       # Hz — Whisper's native rate
AUDIO_CHANNELS = 1              # Mono
AUDIO_CHUNK_SIZE = 1024         # Frames per PyAudio buffer read
VAD_SILENCE_THRESHOLD = 0.005   # RMS amplitude (float32 normalized)
VAD_SILENCE_DURATION_S = 0.8    # Seconds of silence before flushing chunk
VAD_MAX_CHUNK_S = 30            # Max seconds before forcing a flush

# --- Chunking ---

CHUNK_TARGET_TOKENS = 200       # Target token count per RAG chunk
CHUNK_OVERLAP_TOKENS = 40       # Overlap between consecutive chunks

# --- RAG ---

RAG_TOP_K = 5                   # Number of chunks to retrieve per query
RAG_MAX_CONTEXT_TOKENS = 3000   # Max tokens in assembled LLM context
LLM_MAX_NEW_TOKENS = 512        # Max tokens for LLM response

# --- Embedding ---

EMBEDDING_DIM = 768             # nomic-embed-text-v1.5 output dimension

