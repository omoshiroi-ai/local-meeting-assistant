"""ChatScreen — RAG Q&A for a selected meeting."""

import logging

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, RichLog

from src.ui.widgets.chat_panel import ChatPanel

logger = logging.getLogger(__name__)


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
        self._busy = False  # prevent concurrent generations

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
                f"  [dim](Ctrl+T transcript)[/dim]"
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
        if self._busy:
            self.notify("Still generating — please wait.", severity="warning")
            return

        query = event.text
        panel = self.query_one(ChatPanel)
        panel.add_message("user", query)

        if self._session_id:
            self.app.chat_repo.add_message(  # type: ignore[attr-defined]
                self._session_id, "user", query
            )

        self._busy = True
        self._run_rag(query)

    # ------------------------------------------------------------------ #
    # RAG worker
    # ------------------------------------------------------------------ #

    @work(thread=True, name="rag")
    def _run_rag(self, query: str) -> None:
        """Retrieve chunks, build context, stream LLM response. Runs in a thread."""
        from src.rag.chat_service import prepare_rag_stream

        app = self.app
        panel = self.query_one(ChatPanel)

        try:
            prepared = prepare_rag_stream(app.conn, self._meeting_id, query)  # type: ignore[attr-defined]

            if prepared is None:
                app.call_from_thread(
                    panel.add_message,
                    "assistant",
                    "[dim]No relevant transcript segments found for this meeting. "
                    "Make sure the meeting has been recorded and indexed.[/dim]",
                )
                return

            chunk_ids = prepared.chunk_ids

            app.call_from_thread(panel.begin_assistant_stream)
            full_response: list[str] = []

            for token in prepared.token_stream:
                app.call_from_thread(panel.stream_token, token)
                full_response.append(token)

            app.call_from_thread(panel.end_assistant_stream)

            if self._session_id:
                app.call_from_thread(
                    app.chat_repo.add_message,  # type: ignore[attr-defined]
                    self._session_id,
                    "assistant",
                    "".join(full_response),
                    chunk_ids,
                )

        except Exception as exc:
            logger.exception("RAG pipeline failed")
            app.call_from_thread(
                panel.add_message,
                "assistant",
                f"[red]Error: {exc}[/red]",
            )
        finally:
            app.call_from_thread(self._set_not_busy)

    def _set_not_busy(self) -> None:
        self._busy = False
        self.query_one(ChatPanel).focus_input()

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
