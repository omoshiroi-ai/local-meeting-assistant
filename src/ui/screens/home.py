"""HomeScreen — meeting list, entry point for recording and chat."""

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from src.ui.widgets.meeting_list import MeetingList

# Shown while the background check is running
_CHECKING = "[dim]Checking system…[/dim]"


class HomeScreen(Screen):
    """Landing screen: shows past meetings, allows starting a recording or chat."""

    TITLE = "Local Meeting Assistant"
    SUB_TITLE = "Your meetings, locally."

    BINDINGS = [
        Binding("n", "new_recording", "New Recording", priority=True),
        Binding("v", "view_transcript", "Transcript", priority=True),
        Binding("c", "open_chat", "Chat", priority=True),
        Binding("d", "delete_meeting", "Delete", priority=True),
        Binding("r", "refresh", "Refresh", show=False),
        Binding("q", "app.quit", "Quit"),
    ]

    DEFAULT_CSS = """
    #system-status {
        height: 2;
        padding: 0 2;
        background: $surface-darken-1;
        border-top: tall $primary-darken-2;
        color: $text-muted;
        content-align: left middle;
    }
    """

    _selected_meeting_id: int | None = None

    # ------------------------------------------------------------------ #
    # Compose
    # ------------------------------------------------------------------ #

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield MeetingList(id="meeting-list")
        yield Static(_CHECKING, id="system-status", markup=True)
        yield Footer()

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def on_mount(self) -> None:
        self._run_system_check()

    def on_screen_resume(self) -> None:
        """Refresh the meeting list whenever we return from recording or chat."""
        self._selected_meeting_id = None
        self.query_one(MeetingList).refresh_meetings()

    # ------------------------------------------------------------------ #
    # System check worker
    # ------------------------------------------------------------------ #

    @work(thread=True, name="system-check")
    def _run_system_check(self) -> None:
        """Check mic, Whisper model, and embedding model availability."""
        mic_ok, mic_msg = _check_microphone()
        whisper_ok, whisper_msg = _check_whisper_model()
        embed_ok, embed_msg = _check_embedding_model()

        mic_icon = "[green]●[/green]" if mic_ok else "[red]●[/red]"
        whisper_icon = "[green]●[/green]" if whisper_ok else "[red]●[/red]"
        embed_icon = "[green]●[/green]" if embed_ok else "[yellow]●[/yellow]"

        status = (
            f"  {mic_icon} Mic: {mic_msg}"
            f"    {whisper_icon} Whisper: {whisper_msg}"
            f"    {embed_icon} Embeddings: {embed_msg}"
        )
        self.app.call_from_thread(
            self.query_one("#system-status", Static).update, status
        )

        if not mic_ok:
            self.app.call_from_thread(
                self.notify,
                mic_msg,
                severity="error",
                title="Microphone unavailable",
                timeout=10,
            )
        if not whisper_ok:
            self.app.call_from_thread(
                self.notify,
                whisper_msg,
                severity="warning",
                title="Whisper model missing",
                timeout=10,
            )
        if not embed_ok:
            self.app.call_from_thread(
                self.notify,
                embed_msg,
                severity="warning",
                title="Embedding model missing",
                timeout=10,
            )

    # ------------------------------------------------------------------ #
    # Widget events
    # ------------------------------------------------------------------ #

    def on_meeting_list_meeting_selected(self, event: MeetingList.MeetingSelected) -> None:
        self._selected_meeting_id = event.meeting_id

    # ------------------------------------------------------------------ #
    # Actions
    # ------------------------------------------------------------------ #

    def action_new_recording(self) -> None:
        from src.ui.screens.recording import RecordingScreen

        self.app.push_screen(RecordingScreen())

    def action_view_transcript(self) -> None:
        if self._selected_meeting_id is None:
            self.notify("Select a meeting first (use arrow keys).", severity="warning")
            return
        from src.ui.screens.transcript import TranscriptScreen

        self.app.push_screen(TranscriptScreen(self._selected_meeting_id))

    def action_open_chat(self) -> None:
        if self._selected_meeting_id is None:
            self.notify("Select a meeting first (use arrow keys).", severity="warning")
            return
        from src.ui.screens.chat import ChatScreen

        self.app.push_screen(ChatScreen(self._selected_meeting_id))

    def action_delete_meeting(self) -> None:
        if self._selected_meeting_id is None:
            self.notify("Select a meeting first (use arrow keys).", severity="warning")
            return

        self.app.meeting_repo.delete(self._selected_meeting_id)  # type: ignore[attr-defined]
        self._selected_meeting_id = None
        self.query_one(MeetingList).refresh_meetings()
        self.notify("Meeting deleted.")

    def action_refresh(self) -> None:
        self.query_one(MeetingList).refresh_meetings()
        self._run_system_check()


# ------------------------------------------------------------------ #
# Check helpers (pure functions, no UI deps, safe to call from a thread)
# ------------------------------------------------------------------ #


def _check_microphone() -> tuple[bool, str]:
    """Open the mic for 0.5 s and verify it returns non-zero audio."""
    try:
        import time
        import numpy as np
        import sounddevice as sd

        chunks: list[np.ndarray] = []

        def _cb(indata, frames, t, status):
            chunks.append(indata[:, 0].copy())

        with sd.InputStream(
            samplerate=16000, channels=1, dtype="float32",
            blocksize=1024, callback=_cb
        ):
            time.sleep(0.5)

        if not chunks:
            return False, "No audio received from device"

        max_rms = max(float(np.sqrt(np.mean(c ** 2))) for c in chunks)

        if max_rms == 0.0:
            return (
                False,
                "Mic returns silence — grant Terminal microphone access in "
                "System Settings → Privacy & Security → Microphone",
            )

        device = sd.query_devices(kind="input")
        name = device.get("name", "unknown") if isinstance(device, dict) else "unknown"
        return True, f"{name} (RMS {max_rms:.4f})"

    except Exception as exc:
        return False, f"Error: {exc}"


def _check_whisper_model() -> tuple[bool, str]:
    """Check whether the Whisper model weights are in the local HF cache."""
    try:
        from huggingface_hub import snapshot_download
        from huggingface_hub.utils import LocalEntryNotFoundError
        from src.config import WHISPER_MODEL
        from pathlib import Path

        model_dir = Path(WHISPER_MODEL)
        if model_dir.exists():
            return True, f"Ready ({WHISPER_MODEL})"

        try:
            snapshot_download(repo_id=WHISPER_MODEL, local_files_only=True)
            return True, f"Ready ({WHISPER_MODEL})"
        except (LocalEntryNotFoundError, Exception):
            return (
                False,
                f"{WHISPER_MODEL} not downloaded — "
                "run: uv run python scripts/setup_models.py --whisper-only",
            )

    except Exception as exc:
        return False, f"Check failed: {exc}"


def _check_embedding_model() -> tuple[bool, str]:
    """Check whether the nomic-embed-text weights are in the local HF cache."""
    try:
        from huggingface_hub import snapshot_download
        from huggingface_hub.utils import LocalEntryNotFoundError
        from src.config import EMBEDDING_MODEL
        from pathlib import Path

        model_dir = Path(EMBEDDING_MODEL)
        if model_dir.exists():
            return True, f"Ready ({EMBEDDING_MODEL})"

        try:
            snapshot_download(repo_id=EMBEDDING_MODEL, local_files_only=True)
            return True, f"Ready ({EMBEDDING_MODEL})"
        except (LocalEntryNotFoundError, Exception):
            return (
                False,
                f"{EMBEDDING_MODEL} not downloaded — "
                "run: uv run python scripts/setup_models.py",
            )

    except Exception as exc:
        return False, f"Check failed: {exc}"
