# Local Meeting Assistant - Implementation Plan

## Architecture Overview

**3 MLX models, all running locally on Apple Silicon:**

| Role | Model | Size | Why |
|---|---|---|---|
| STT | `mlx-community/whisper-large-v3-turbo` | ~800M | 8x faster than large-v3, ~2-4% WER |
| Embeddings | `mlx-community/nomic-embed-text-v1.5` | ~137M | 8192 context, great semantic retrieval |
| Chat LLM | `mlx-community/Qwen2.5-7B-Instruct-4bit` | ~4.5GB | 128K context, strong Q&A, ~40 tok/s |

---

## Project Structure

```
local-meeting-assistant/
├── pyproject.toml
├── src/
│   ├── main.py                    # Entrypoint
│   ├── config.py                  # Model IDs, paths, constants
│   ├── db/
│   │   ├── schema.py              # SQLite DDL
│   │   ├── migrations.py          # Version-tracked migrations
│   │   └── repository.py          # All SQL ops (meetings, segments, chunks, chat)
│   ├── audio/
│   │   ├── capture.py             # sounddevice mic loop → queue
│   │   ├── vad.py                 # Energy VAD, accumulate ~10-30s speech chunks
│   │   └── transcriber.py         # mlx-whisper wrapper, runs in thread
│   ├── indexing/
│   │   ├── chunker.py             # Sliding window ~200 tokens, 40 overlap (tiktoken)
│   │   ├── embedder.py            # nomic-embed-text wrapper, batch encode
│   │   └── vector_store.py        # FAISS IndexFlatIP CRUD + persist
│   ├── rag/
│   │   ├── retriever.py           # query embed → FAISS search → hydrate from DB
│   │   ├── context_builder.py     # Assemble chunks into LLM prompt with citations
│   │   └── llm.py                 # Qwen streaming generate wrapper
│   ├── triggers/
│   │   └── zoom_watcher.py        # psutil polls for Zoom process, fires events
│   └── ui/
│       ├── app.py                 # Textual App, screen routing, shared state
│       ├── screens/
│       │   ├── home.py            # Meeting list + "New Recording" button
│       │   ├── recording.py       # Live transcript + timer + VAD indicator
│       │   └── chat.py            # RAG chat, two-panel layout
│       └── widgets/
│           ├── transcript_log.py  # Auto-scroll RichLog widget
│           ├── meeting_list.py    # DataTable of past meetings
│           └── chat_panel.py      # Input + streaming response display
├── data/
│   ├── meetings.db
│   └── faiss/meetings.index
└── scripts/
    ├── setup_models.py            # Pre-download all 3 models
    └── reindex.py                 # Rebuild FAISS from DB (after model upgrades)
```

---

## Database Schema (SQLite)

```sql
-- meetings: one row per recorded meeting session
CREATE TABLE meetings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL DEFAULT '',
    source          TEXT NOT NULL DEFAULT 'manual',    -- 'zoom', 'manual', 'teams'
    started_at      TEXT NOT NULL,                     -- ISO-8601 UTC timestamp
    ended_at        TEXT,                              -- NULL while recording is active
    duration_secs   INTEGER GENERATED ALWAYS AS (
                        CAST((JULIANDAY(ended_at) - JULIANDAY(started_at)) * 86400 AS INTEGER)
                    ) VIRTUAL,
    notes           TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- transcript_segments: raw STT output, immutable
CREATE TABLE transcript_segments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id      INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    sequence_num    INTEGER NOT NULL,
    speaker_label   TEXT,
    text            TEXT NOT NULL,
    start_ms        INTEGER NOT NULL,
    end_ms          INTEGER NOT NULL,
    confidence      REAL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(meeting_id, sequence_num)
);

-- transcript_chunks: derived RAG chunks, rebuildable from segments
CREATE TABLE transcript_chunks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id      INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    chunk_index     INTEGER NOT NULL,
    text            TEXT NOT NULL,
    start_ms        INTEGER NOT NULL,
    end_ms          INTEGER NOT NULL,
    token_count     INTEGER NOT NULL,
    embedding_dim   INTEGER NOT NULL DEFAULT 768,
    faiss_row_id    INTEGER,                           -- row index in FAISS index
    indexed_at      TEXT,                              -- NULL until embedded+indexed
    UNIQUE(meeting_id, chunk_index)
);

-- chat_sessions: one per user Q&A session
CREATE TABLE chat_sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id      INTEGER REFERENCES meetings(id) ON DELETE SET NULL,  -- NULL = cross-meeting
    started_at      TEXT NOT NULL DEFAULT (datetime('now')),
    ended_at        TEXT
);

-- chat_messages: each turn in a chat session
CREATE TABLE chat_messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    content         TEXT NOT NULL,
    retrieved_chunk_ids TEXT,                          -- JSON array of chunk IDs used as context
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- app_state: key-value store for persistent UI state
CREATE TABLE app_state (
    key             TEXT PRIMARY KEY,
    value           TEXT NOT NULL,
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Indexes
CREATE INDEX idx_segments_meeting ON transcript_segments(meeting_id, sequence_num);
CREATE INDEX idx_chunks_meeting   ON transcript_chunks(meeting_id, chunk_index);
CREATE INDEX idx_chunks_faiss     ON transcript_chunks(faiss_row_id) WHERE faiss_row_id IS NOT NULL;
CREATE INDEX idx_messages_session ON chat_messages(session_id, created_at);
CREATE INDEX idx_meetings_started ON meetings(started_at DESC);
```

### Schema Design Notes

- `transcript_segments` preserves raw Whisper output verbatim — never mutated after insert
- `transcript_chunks` is the derived RAG layer — can be rebuilt from segments via `scripts/reindex.py`
- `faiss_row_id` bridges SQLite metadata and the FAISS binary index
- `chat_messages.retrieved_chunk_ids` stores the evidence trail as a JSON array (e.g., `[12, 47, 103]`) so the UI can highlight source segments

---

## Data Flows

**Recording:**
```
Mic → sounddevice → VAD → speech_queue → mlx-whisper (thread) → DB insert + TUI update
```

**Post-meeting indexing (background worker):**
```
segments → chunker → embed (nomic) → FAISS.add → update faiss_row_id in DB
```

**RAG Chat:**
```
query → embed → FAISS.search(k=5) → fetch chunks from DB → build context → Qwen streaming
```

---

## Threading Model

All MLX calls run in **Textual Workers** (sync threads), never on the asyncio main thread. `call_from_thread` bridges results back to the TUI.

**Golden rule: never block the event loop with `mx.eval()`.**

```
Main Thread (Textual event loop - asyncio)
├── UI rendering and event handling
├── DB reads (fast, synchronous sqlite3)
└── Worker threads (via Textual Worker):
    ├── AudioCapture thread   → sounddevice callback
    ├── Transcription thread  → MLX Whisper
    ├── Indexing thread       → MLX Embedder + FAISS (post-meeting)
    └── LLM thread            → MLX Qwen streaming generate
```

---

## Key Implementation Details

### Audio Pipeline

Whisper performs best on 10-30 second chunks. The VAD accumulates speech until a pause >0.8s, then flushes to the transcription thread.

### Chunking Strategy

Sliding window of ~200 tokens with 40-token overlap (measured via `tiktoken`). The two-table design (segments + chunks) means chunking strategy can be changed and rebuilt without losing raw data.

### FAISS Strategy

Start with `IndexFlatIP` (exact cosine similarity on L2-normalized vectors). Upgrade to `IndexIVFFlat` (nlist=100) if the index grows beyond ~50 meetings / 500K chunks.

### RAG System Prompt

```
You are a meeting assistant. Answer questions about the user's meetings using ONLY the
provided transcript excerpts. If the answer is not in the excerpts, say so. Be concise
and cite the meeting name and timestamp when referencing specific content.

Transcript excerpts:
{context}
```

### Zoom Detection

`zoom_watcher.py` uses `psutil.process_iter()` to poll every 2s for the `zoom.us` process. Checks for `CptHost` subprocess to distinguish active meetings from Zoom just being open. Debounced to handle brief disappearances during screen shares.

---

## Dependencies

```toml
[project.dependencies]
# ML stack
mlx = ">=0.24.0"
mlx-lm = ">=0.21.0"           # Covers Qwen LLM + nomic embeddings
mlx-whisper = ">=0.4.1"

# Vector search
faiss-cpu = ">=1.9.0"         # No Metal/MPS support in FAISS; MLX handles GPU for ML
numpy = ">=2.0.0"

# Audio
sounddevice = ">=0.5.0"       # Requires: brew install portaudio
soundfile = ">=0.12.0"

# TUI
textual = ">=1.0.0"           # 1.x API (Workers, reactive system)

# Text processing
tiktoken = ">=0.9.0"

# Utilities
huggingface-hub = ">=0.26.0"
psutil = ">=6.0.0"
tqdm = ">=4.67.0"
```

**Pre-install steps:**
```bash
brew install portaudio
uv sync
uv run python scripts/setup_models.py  # Downloads ~6 GB of model weights
```

---

## Implementation Phases

| Phase | What | Duration |
|---|---|---|
| 0 | Project scaffold + DB layer + tests | 2-3 days |
| 1 | Textual TUI shell (static/mocked data) | 3-4 days |
| 2 | Audio capture + live STT transcription | 4-5 days |
| 3 | Zoom auto-trigger (psutil watcher) | 1-2 days |
| 4 | Post-meeting chunking + FAISS indexing | 3-4 days |
| 5 | RAG chat screen | 3-4 days |
| 6 | Polish, error handling, tests | 3-5 days |

**Total: ~3-4 weeks of focused development**

Start with Phase 0 — the DB repository layer is the foundation everything else depends on.
