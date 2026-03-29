# Local Meeting Assistant

A fully local, privacy-first meeting assistant for Apple Silicon Macs. Records your meetings, transcribes them in real time using Whisper, and lets you chat with past meetings using a RAG pipeline — all running on-device with no cloud calls.

```
┌─────────────────────────────────────────────────────┐
│  Local Meeting Assistant          12:34:56           │
├─────────────────────────────────────────────────────┤
│  # Meeting List                                      │
│  ▶ Weekly Sync          2026-03-27   12m 04s         │
│    Design Review        2026-03-26   45m 11s         │
│    Sprint Planning      2026-03-25   1h 02m          │
├─────────────────────────────────────────────────────┤
│  ● Mic: MacBook Pro Mic   ● Whisper: Ready           │
│  ● Embed: Ready           ● LLM: Ready               │
└─────────────────────────────────────────────────────┘
  N New Recording  V Transcript  C Chat  D Delete  Q Quit
```

## Features

- **Real-time transcription** — Whisper Large v3 Turbo via MLX, ~2-4% word error rate
- **Live audio meter** — RMS bar and VAD indicator so you can see the mic working
- **Searchable history** — all meetings stored locally in SQLite, browsable with arrow keys
- **RAG chat** — ask questions about any past meeting; Qwen2.5-7B streams answers with timestamps
- **Post-meeting indexing** — automatic chunking + FAISS indexing runs in the background after you stop
- **100% local** — no API keys, no cloud, nothing leaves your Mac
- **Web UI** — optional Vite + React + TypeScript UI using `@nqlib/nqui`, talking to a local FastAPI layer (`/api/sessions`, SSE chat, health)

## Models

| Role | Model | Size | Notes |
|---|---|---|---|
| STT | `mlx-community/whisper-large-v3-turbo` | ~800 MB | Required for recording |
| Embeddings | `nomic-ai/nomic-embed-text-v1.5` | ~275 MB | Required for RAG chat |
| Chat LLM | `mlx-community/Qwen2.5-7B-Instruct-4bit` | ~4.5 GB | Required for RAG chat |

**Total download: ~5.6 GB** on first run.

---

## Requirements

- **macOS** with Apple Silicon (M1 or later)
- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** package manager
- **portaudio** (for microphone access)
- **Microphone permission** granted to Terminal (or your terminal app)

---

## Setup

### 1. Install system dependencies

```bash
brew install portaudio
```

### 2. Clone and install Python dependencies

```bash
git clone <repo-url>
cd local-meeting-assistant
uv sync
```

### 3. Download models

Download all three models (~5.6 GB total):

```bash
uv run python scripts/setup_models.py
```

To download only Whisper (for recording without RAG chat):

```bash
uv run python scripts/setup_models.py --whisper-only
```

Models are cached in `~/.cache/huggingface/hub/` and only downloaded once.

### 4. Grant microphone access

On first launch, macOS will prompt for microphone permission. If the mic check shows red:

1. Open **System Settings → Privacy & Security → Microphone**
2. Enable access for **Terminal** (or iTerm2, Ghostty, etc.)

### 5. Run the app

```bash
uv run meeting-assistant
```

### 6. Web UI + API (optional)

Recordings are stored as **sessions** in SQLite (SSOT: same `meetings` table with `session_type`, `department_id`, `metadata`, `wbs_node_id`, `case_id` for future work/CS flows). The browser UI lists sessions, shows transcripts, runs RAG chat, and reindexes. **Live capture still uses the Textual app** above.

**Terminal 1 — Python API** (binds to `127.0.0.1` only, default port `8765`):

```bash
uv run meeting-assistant-api
```

Override host/port with `MEETING_API_HOST` / `MEETING_API_PORT` if needed.

**Terminal 2 — Vite frontend** (`web/`):

```bash
cd web
npm install
npm run dev
```

Open the printed local URL (e.g. `http://localhost:5173`). The dev server proxies `/api` to the API.

**Production-style**: build the web app (`cd web && npm run build`), then either serve `web/dist` with any static server or mount it from a future FastAPI static route; the API must stay on the same origin or CORS must be configured.

---

## Usage

### Home screen

| Key | Action |
|---|---|
| `N` | Start a new recording |
| `V` | View transcript for selected meeting |
| `C` | Open RAG chat for selected meeting |
| `D` | Delete selected meeting |
| `R` | Refresh list and re-run system check |
| `Q` | Quit |

Use **arrow keys** to navigate the meeting list.

The status bar shows four indicators:

- **Mic** — green if microphone is working
- **Whisper** — green if the STT model is cached locally
- **Embed** — green if the embedding model is cached locally
- **LLM** — green if the Qwen chat model is cached locally

Red = feature unavailable. Yellow = missing but recording still works.

### Recording screen

Press `N` to start recording. The screen shows a live RMS meter, VAD indicator (Speaking / Silence), and a live transcript that updates as Whisper processes each speech segment.

| Key | Action |
|---|---|
| `S` or `Escape` | Stop recording and save |
| `T` | Edit the meeting title |
| `Enter` | Save the title |

After stopping, the meeting is saved and background indexing starts automatically. A notification appears when the meeting is ready for chat.

> **Note:** The first transcription after pressing N takes a few extra seconds while Whisper loads into memory. Subsequent segments are faster.

### Transcript screen

Press `V` (with a meeting selected) to view the full transcript with timestamps.

| Key | Action |
|---|---|
| `Escape` | Go back |
| `G` | Scroll to top |
| `Shift+G` | Scroll to bottom |

### Chat screen

Press `C` (with a meeting selected) to open RAG chat. Type a question and press `Enter`. The assistant retrieves the most relevant transcript segments and streams a response.

| Key | Action |
|---|---|
| `Escape` | Go back |
| `Ctrl+T` | View full transcript |
| `Ctrl+L` | Clear chat history |

**Example questions:**
- "What action items were assigned?"
- "What was decided about the Q3 roadmap?"
- "Who is responsible for the design review?"
- "Summarise the key points from this meeting."

---

## Configuration

All settings are in `src/config.py`. Override any of them with environment variables:

| Variable | Default | Description |
|---|---|---|
| `WHISPER_MODEL` | `mlx-community/whisper-large-v3-turbo` | Whisper model HF repo ID |
| `EMBEDDING_MODEL` | `nomic-ai/nomic-embed-text-v1.5` | Embedding model HF repo ID |
| `LLM_MODEL` | `mlx-community/Qwen2.5-7B-Instruct-4bit` | LLM HF repo ID |
| `MEETING_DATA_DIR` | `./data` | Directory for SQLite DB and FAISS index |
| `MEETING_API_HOST` | `127.0.0.1` | Bind address for `meeting-assistant-api` |
| `MEETING_API_PORT` | `8765` | Port for the FastAPI server |

Example — use a smaller Whisper model:

```bash
WHISPER_MODEL=mlx-community/whisper-small uv run meeting-assistant
```

---

## Data

All data lives in `data/` (gitignored). Each **recording** is one row in `meetings` (SSOT session id) with optional `session_type` (`meeting`, `work_process`, `customer_service`), `department_id`, JSON `metadata`, `wbs_node_id`, and `case_id` for future technician / CS workflows.

```
data/
├── meetings.db          # SQLite: meetings, segments, chunks, chat history
└── faiss/
    ├── meetings.index   # FAISS vector index
    └── meetings.meta.json
```

To rebuild the FAISS index from scratch (e.g. after upgrading the embedding model):

```bash
uv run python scripts/reindex.py

# Re-index a single meeting
uv run python scripts/reindex.py --meeting-id 42
```

---

## Troubleshooting

**Mic shows red / no transcript appears**

Check System Settings → Privacy & Security → Microphone and enable access for your terminal app. Press `R` to re-run the system check.

**"Whisper model missing" warning**

```bash
uv run python scripts/setup_models.py --whisper-only
```

**"Embedding/LLM model missing" warning**

```bash
uv run python scripts/setup_models.py
```

**VAD shows "Silence" even while speaking**

The default threshold is tuned for close-mic audio. For a room mic, lower it in `src/config.py`:

```python
VAD_SILENCE_THRESHOLD = 0.002
```

**Chat returns "No relevant transcript segments found"**

The meeting hasn't been indexed yet. Wait for the "Indexing complete" notification after recording, or run manually:

```bash
uv run python scripts/reindex.py --meeting-id <id>
```

**View debug logs**

```bash
tail -f /tmp/meeting_assistant.log
```

---

## Running tests

```bash
uv run pytest
```

66 tests covering the DB layer, VAD, chunker, and RAG context builder. No microphone or model downloads required.
