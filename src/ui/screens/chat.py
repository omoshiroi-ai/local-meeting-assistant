"""ChatScreen — RAG Q&A for a selected meeting."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, RichLog

from src.ui.widgets.chat_panel import ChatPanel


class ChatScreen(Screen):
    """Full-width chat panel with a compact metadata header bar."""

    TITLE = "Chat"

    BINDINGS = [
        Binding("escape", "go_back", "Back", priority=True),
        Binding("ctrl+l", "clear_chat", "Clear", show=False),
        Binding("ctrl+t", "view_transcript", "Transcript"),
    ]

    DEFAULT_CSS = """
    ChatScreen { layout: vertical; }

    #meta-bar {
        height: 3;
        padding: 0 2;
        content-align: left middle;
        background: $surface-darken-1;
        border-bottom: tall $primary;
        color: $text-muted;
    }

    ChatPanel {
        height: 1fr;
    }
    """

    def __init__(self, meeting_id: int) -> None:
        super().__init__()
        self._meeting_id = meeting_id
        self._session_id: int | None = None

    # ------------------------------------------------------------------ #
    # Compose
    # ------------------------------------------------------------------ #

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Label("", id="meta-bar")
        yield ChatPanel(id="chat-panel")
        yield Footer()

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def on_mount(self) -> None:
        meeting = self.app.meeting_repo.get(self._meeting_id)  # type: ignore[attr-defined]
        if meeting:
            seg_count = self.app.segment_repo.count_by_meeting(self._meeting_id)  # type: ignore[attr-defined]
            duration_str = "in progress"
            if meeting.duration_secs is not None:
                mins, secs = divmod(meeting.duration_secs, 60)
                duration_str = f"{mins}m {secs:02d}s" if mins else f"{secs}s"
            self.query_one("#meta-bar", Label).update(
                f"[bold]{meeting.title or 'Untitled'}[/bold]"
                f"  ·  {meeting.started_at[:10]}"
                f"  ·  {duration_str}"
                f"  ·  {seg_count} segments"
                f"  [dim](Ctrl+T to view full transcript)[/dim]"
            )
            self.sub_title = meeting.title or "Untitled"

        self._session_id = self.app.chat_repo.create_session(  # type: ignore[attr-defined]
            meeting_id=self._meeting_id
        )
        self.query_one(ChatPanel).focus_input()

    # ------------------------------------------------------------------ #
    # Events
    # ------------------------------------------------------------------ #

    def on_chat_panel_chat_submit(self, event: ChatPanel.ChatSubmit) -> None:
        panel = self.query_one(ChatPanel)
        query = event.text

        if self._session_id:
            self.app.chat_repo.add_message(self._session_id, "user", query)  # type: ignore[attr-defined]

        panel.add_message("user", query)

        # Phase 5 will replace this with the real RAG + LLM pipeline
        placeholder = (
            "[dim]RAG chat integration arrives in Phase 5.\n"
            "The pipeline will embed your query, search FAISS for relevant\n"
            "transcript chunks, and stream a response from Qwen2.5-7B.[/dim]"
        )
        panel.add_message("assistant", placeholder)

        if self._session_id:
            self.app.chat_repo.add_message(  # type: ignore[attr-defined]
                self._session_id, "assistant", placeholder
            )

    # ------------------------------------------------------------------ #
    # Actions
    # ------------------------------------------------------------------ #

    def action_go_back(self) -> None:
        if self._session_id:
            self.app.chat_repo.end_session(self._session_id)  # type: ignore[attr-defined]
        self.app.pop_screen()

    def action_view_transcript(self) -> None:
        from src.ui.screens.transcript import TranscriptScreen

        self.app.push_screen(TranscriptScreen(self._meeting_id))

    def action_clear_chat(self) -> None:
        self.query_one(ChatPanel).query_one(RichLog).clear()
        self.notify("Chat cleared.")
