"""HomeScreen — meeting list, entry point for recording and chat."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header

from src.ui.widgets.meeting_list import MeetingList


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

    _selected_meeting_id: int | None = None

    # ------------------------------------------------------------------ #
    # Compose
    # ------------------------------------------------------------------ #

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield MeetingList(id="meeting-list")
        yield Footer()

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def on_screen_resume(self) -> None:
        """Refresh the list whenever we return from recording or chat."""
        self._selected_meeting_id = None
        self.query_one(MeetingList).refresh_meetings()

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
        self.notify("Refreshed.")
