"""TranscriptScreen — full scrollable transcript for a past meeting."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, RichLog, Static


class TranscriptScreen(Screen):
    """Read-only view of every saved segment for one meeting."""

    TITLE = "Transcript"

    BINDINGS = [
        Binding("escape", "go_back", "Back", priority=True),
        Binding("g", "scroll_top", "Top", show=False),
        Binding("G", "scroll_bottom", "Bottom", show=False),
    ]

    DEFAULT_CSS = """
    TranscriptScreen { layout: vertical; }

    #meta-bar {
        height: 3;
        padding: 0 2;
        content-align: left middle;
        background: $surface-darken-1;
        border-bottom: tall $primary;
        color: $text-muted;
    }

    #transcript-view {
        height: 1fr;
        padding: 1 2;
        border: blank;
    }
    """

    def __init__(self, meeting_id: int) -> None:
        super().__init__()
        self._meeting_id = meeting_id

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("", id="meta-bar")
        yield RichLog(id="transcript-view", markup=True, highlight=False, wrap=True)
        yield Footer()

    def on_mount(self) -> None:
        meeting = self.app.meeting_repo.get(self._meeting_id)  # type: ignore[attr-defined]
        if not meeting:
            return

        if meeting.duration_secs is not None:
            mins, secs = divmod(meeting.duration_secs, 60)
            duration_str = f"{mins}m {secs:02d}s"
        else:
            duration_str = "in progress"

        title = meeting.title or "Untitled"
        date = meeting.started_at[:10]
        self.query_one("#meta-bar", Static).update(
            f"[bold]{title}[/bold]  ·  {date}  ·  {duration_str}  ·  {meeting.source}"
        )
        self.sub_title = title

        segments = self.app.segment_repo.get_by_meeting(self._meeting_id)  # type: ignore[attr-defined]
        log = self.query_one(RichLog)

        if not segments:
            log.write("[dim]No transcript segments found for this meeting.[/dim]")
            log.write("")
            log.write("[dim]Possible reasons:[/dim]")
            log.write("[dim]  • The Whisper model was still loading when you spoke[/dim]")
            log.write("[dim]  • No microphone input was detected[/dim]")
            log.write("[dim]  • Recording was stopped before any speech was transcribed[/dim]")
            return

        log.write(f"[dim]── {len(segments)} segment(s) ──[/dim]")
        log.write("")
        for seg in segments:
            mins, secs = divmod(seg.start_ms // 1000, 60)
            ts = f"{mins:02d}:{secs:02d}"
            log.write(f"[dim cyan]{ts}[/dim cyan]  {seg.text}")

        log.scroll_home(animate=False)

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_scroll_top(self) -> None:
        self.query_one(RichLog).scroll_home(animate=True)

    def action_scroll_bottom(self) -> None:
        self.query_one(RichLog).scroll_end(animate=True)
