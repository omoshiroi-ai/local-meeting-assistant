"""RecordingScreen — live transcript view with real audio capture and STT.

Audio pipeline (all off the main thread):
  sounddevice callback → AudioCapture queue
    → EnergyVAD (in _audio_pipeline worker thread)
      → Transcriber.transcribe() (blocking MLX call, same thread)
        → call_from_thread → append_transcription() → DB + TranscriptLog
"""

import threading
import time
import logging

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, Label, Static
from textual.worker import Worker, WorkerState

from src.ui.widgets.transcript_log import TranscriptLog

logger = logging.getLogger(__name__)


class RecordingScreen(Screen):
    """Active recording session screen."""

    TITLE = "Recording"

    BINDINGS = [
        Binding("s", "stop_recording", "Stop Recording", priority=True),
        Binding("escape", "stop_recording", "Stop Recording", show=False),
        Binding("t", "focus_title", "Edit Title"),
    ]

    DEFAULT_CSS = """
    RecordingScreen { layout: vertical; }

    #status-bar {
        height: 3;
        padding: 0 2;
        content-align: left middle;
        background: $surface-darken-1;
        border-bottom: tall $primary;
        color: $text;
    }

    #title-input {
        height: 3;
        margin: 1 2 0 2;
        border: tall $primary-darken-2;
    }

    #transcript-log { height: 1fr; }

    #vad-bar {
        height: 1;
        padding: 0 2;
        background: $surface-darken-2;
        color: $text-muted;
        content-align: left middle;
    }
    """

    _elapsed: reactive[int] = reactive(0)

    def __init__(self) -> None:
        super().__init__()
        self._meeting_id: int | None = None
        self._stop_event = threading.Event()
        self._recording_start: float = 0.0
        self._pipeline_worker: Worker | None = None
        self._segment_count: int = 0
        self._last_rms: float = 0.0

    # ------------------------------------------------------------------ #
    # Compose
    # ------------------------------------------------------------------ #

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("", id="status-bar")
        yield Input(
            placeholder="Meeting title (optional — press T to edit, Enter to save)",
            id="title-input",
        )
        yield TranscriptLog(id="transcript-log", markup=True, highlight=False, wrap=True)
        yield Label("", id="vad-bar")
        yield Footer()

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def on_mount(self) -> None:
        self._meeting_id = self.app.meeting_repo.create(source="manual")  # type: ignore[attr-defined]
        self._recording_start = time.monotonic()

        self._update_status("Initialising…")
        self.query_one("#vad-bar", Label).update(_vad_bar(False))
        self.set_interval(1.0, self._tick_timer)

        # Keep focus on the log so S/Escape bindings fire immediately.
        # User presses T to explicitly move focus to the title input.
        self.query_one(TranscriptLog).focus()

        # Launch the audio pipeline in a background thread
        self._pipeline_worker = self._run_audio_pipeline()

    def on_unmount(self) -> None:
        self._stop_event.set()

    # ------------------------------------------------------------------ #
    # Timer
    # ------------------------------------------------------------------ #

    def _tick_timer(self) -> None:
        self._elapsed += 1
        self._refresh_status_bar()

    def _refresh_status_bar(self) -> None:
        h = self._elapsed // 3600
        m = (self._elapsed % 3600) // 60
        s = self._elapsed % 60
        rms_bar = _rms_bar(self._last_rms)
        segs = f"  [dim]{self._segment_count} segment{'s' if self._segment_count != 1 else ''}[/dim]"
        self.query_one("#status-bar", Static).update(
            f"[red bold]●[/red bold] REC  [dim]{h:02d}:{m:02d}:{s:02d}[/dim]"
            f"  {rms_bar}{segs}"
        )

    def _update_status(self, text: str) -> None:
        self.query_one("#status-bar", Static).update(text)

    # ------------------------------------------------------------------ #
    # Audio pipeline worker
    # ------------------------------------------------------------------ #

    @work(thread=True, name="audio-pipeline", exclusive=True)
    def _run_audio_pipeline(self) -> None:
        """Runs entirely in a worker thread.  Touches the UI only via call_from_thread."""
        from src.audio.capture import AudioCapture
        from src.audio.transcriber import Transcriber
        from src.audio.vad import EnergyVAD
        from src.config import WHISPER_MODEL

        # --- Load Whisper model first (may take time on first download) ---
        app = self.app
        app.call_from_thread(
            self._update_status,
            "[yellow]Loading Whisper model… (first run downloads ~800 MB)[/yellow]",
        )
        transcriber = Transcriber(WHISPER_MODEL)
        try:
            transcriber.load()
        except Exception as exc:
            logger.exception("Failed to load Whisper model")
            app.call_from_thread(
                self._update_status, f"[red]Model load failed: {exc}[/red]"
            )
            return

        # --- Open microphone ---
        capture = AudioCapture()
        try:
            capture.start()
        except Exception as exc:
            logger.exception("Failed to open microphone")
            app.call_from_thread(
                self._update_status, f"[red]Microphone error: {exc}[/red]"
            )
            return

        app.call_from_thread(
            self._update_status,
            "[red bold]●[/red bold] REC  [dim]00:00:00[/dim]",
        )

        log = self.query_one(TranscriptLog)
        app.call_from_thread(log.append_status, "Listening… speak now.")

        vad = EnergyVAD()
        import numpy as np
        _ui_tick = 0  # throttle: update VAD bar every N chunks (~5 Hz)

        try:
            while not self._stop_event.is_set():
                chunk = capture.read_chunk(timeout=0.05)
                if chunk is None:
                    continue

                rms = float(np.sqrt(np.mean(chunk ** 2)))
                result = vad.process(chunk)

                # Update VAD bar at ~5 Hz to avoid flooding the event loop
                _ui_tick += 1
                if _ui_tick % 16 == 0:
                    self._last_rms = rms
                    app.call_from_thread(self.set_vad_active, result.is_speech)
                    app.call_from_thread(self._refresh_status_bar)

                if result.audio is not None:
                    offset_ms = int(result.offset_samples / capture.sample_rate * 1000)
                    transcription = transcriber.transcribe(result.audio, offset_ms=offset_ms)
                    if transcription and transcription.text:
                        app.call_from_thread(
                            self.append_transcription,
                            transcription.text,
                            transcription.offset_ms,
                        )

            # Flush any remaining audio when stop is signalled
            final = vad.flush()
            if final.audio is not None:
                offset_ms = int(final.offset_samples / capture.sample_rate * 1000)
                transcription = transcriber.transcribe(final.audio, offset_ms=offset_ms)
                if transcription and transcription.text:
                    app.call_from_thread(
                        self.append_transcription,
                        transcription.text,
                        transcription.offset_ms,
                    )

        finally:
            capture.stop()
            app.call_from_thread(self.set_vad_active, False)
            logger.info("Audio pipeline stopped.")

    # ------------------------------------------------------------------ #
    # Called from worker thread via call_from_thread
    # ------------------------------------------------------------------ #

    def append_transcription(self, text: str, offset_ms: int) -> None:
        """Persist a segment and update the transcript log. Runs on main thread."""
        if not self._meeting_id:
            return
        seg_repo = self.app.segment_repo  # type: ignore[attr-defined]
        seq = seg_repo.next_sequence_num(self._meeting_id)
        end_ms = int((time.monotonic() - self._recording_start) * 1000)
        seg_repo.insert(self._meeting_id, seq, text, offset_ms, end_ms)
        self._segment_count += 1
        self.query_one(TranscriptLog).append_segment(text, offset_ms)
        self._refresh_status_bar()

    def set_vad_active(self, active: bool) -> None:
        """Update the VAD bar. Runs on main thread."""
        self.query_one("#vad-bar", Label).update(_vad_bar(active))

    # ------------------------------------------------------------------ #
    # Events
    # ------------------------------------------------------------------ #

    def on_input_submitted(self, event: Input.Submitted) -> None:
        title = event.value.strip()
        if title and self._meeting_id:
            self.app.meeting_repo.update_title(self._meeting_id, title)  # type: ignore[attr-defined]
            self.notify(f'Title set to "{title}"')
        self.query_one(TranscriptLog).focus()

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.worker.name == "audio-pipeline" and event.state == WorkerState.ERROR:
            self.notify("Audio pipeline error — check logs.", severity="error")

    # ------------------------------------------------------------------ #
    # Actions
    # ------------------------------------------------------------------ #

    def action_stop_recording(self) -> None:
        # Signal the pipeline to stop and wait briefly for it to flush
        self._stop_event.set()

        if self._meeting_id:
            title = self.query_one(Input).value.strip()
            repo = self.app.meeting_repo  # type: ignore[attr-defined]
            if title:
                repo.update_title(self._meeting_id, title)
            repo.end(self._meeting_id)
            self.notify(f"Meeting saved (ID: {self._meeting_id}).")
            self._run_indexing(self._meeting_id)

        self.app.pop_screen()

    @work(thread=True, name="indexing")
    def _run_indexing(self, meeting_id: int) -> None:
        """Chunk, embed, and FAISS-index the meeting in the background."""
        from src.indexing.pipeline import index_meeting

        try:
            n = index_meeting(meeting_id, self.app.conn)  # type: ignore[attr-defined]
            logger.info("Indexing complete: %d chunks for meeting %d", n, meeting_id)
            if n > 0:
                self.app.call_from_thread(
                    self.app.notify,
                    f"Meeting indexed: {n} chunks ready for chat.",
                    title="Indexing complete",
                    timeout=5,
                )
        except Exception as exc:
            logger.exception("Indexing failed for meeting %d", meeting_id)
            self.app.call_from_thread(
                self.app.notify,
                f"Indexing failed: {exc}",
                severity="warning",
                title="Indexing error",
                timeout=8,
            )

    def action_focus_title(self) -> None:
        self.query_one(Input).focus()


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #


def _vad_bar(active: bool) -> str:
    if active:
        return "  VAD [bold green]●●●●○[/bold green]  Speaking"
    return "  VAD [dim]○○○○○[/dim]  Silence"


def _rms_bar(rms: float) -> str:
    """Visual RMS level indicator, e.g. ▁▃▅▇ RMS:0.0123"""
    level = min(int(rms * 1000), 8)  # 0-8 blocks
    blocks = "▁▂▃▄▅▆▇█"
    filled = blocks[level - 1] if level > 0 else " "
    color = "green" if rms > 0.005 else "dim"
    return f"[{color}]{filled * level}[/{color}] [dim]RMS:{rms:.4f}[/dim]"
