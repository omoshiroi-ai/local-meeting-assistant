"""MeetingList — DataTable wrapper for browsing past meetings."""

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import DataTable, Label


class MeetingList(Widget):
    """Displays all meetings in a sortable DataTable.

    Posts a ``MeetingList.MeetingSelected`` message when the user moves the
    cursor, so parent screens can track which meeting is active.
    """

    DEFAULT_CSS = """
    MeetingList {
        height: 1fr;
    }

    MeetingList DataTable {
        height: 1fr;
    }

    MeetingList #empty-label {
        height: 1fr;
        content-align: center middle;
        color: $text-muted;
    }
    """

    # ------------------------------------------------------------------ #
    # Messages
    # ------------------------------------------------------------------ #

    class MeetingSelected(Message):
        """Fired when the cursor lands on a row (including keyboard nav)."""

        def __init__(self, meeting_id: int) -> None:
            self.meeting_id = meeting_id
            super().__init__()

    # ------------------------------------------------------------------ #
    # Compose & mount
    # ------------------------------------------------------------------ #

    def compose(self) -> ComposeResult:
        yield DataTable(id="meetings-table", cursor_type="row", zebra_stripes=True)
        yield Label(
            "No meetings yet.\n\nPress [b]N[/b] to start a new recording.",
            id="empty-label",
            markup=True,
        )

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_column("Title", width=28, key="title")
        table.add_column("Date", width=12, key="date")
        table.add_column("Duration", width=10, key="duration")
        table.add_column("Segments", width=10, key="segments")
        table.add_column("Source", width=8, key="source")
        self.refresh_meetings()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def refresh_meetings(self) -> None:
        """Reload the table from the database."""
        # Import here to avoid circular imports at module level
        from src.db.repository import MeetingRepo, SegmentRepo

        app = self.app
        meeting_repo: MeetingRepo = app.meeting_repo  # type: ignore[attr-defined]
        segment_repo: SegmentRepo = app.segment_repo  # type: ignore[attr-defined]

        meetings = meeting_repo.list_all()
        table = self.query_one(DataTable)
        table.clear()

        empty_label = self.query_one("#empty-label", Label)

        if not meetings:
            empty_label.display = True
            return

        empty_label.display = False
        for m in meetings:
            if m.duration_secs is not None:
                mins = m.duration_secs // 60
                secs = m.duration_secs % 60
                duration_str = f"{mins}m {secs:02d}s" if mins else f"{secs}s"
            else:
                duration_str = "live…"

            date_str = m.started_at[:10]
            seg_count = segment_repo.count_by_meeting(m.id)

            table.add_row(
                m.title or "Untitled",
                date_str,
                duration_str,
                str(seg_count),
                m.source,
                key=str(m.id),
            )

        # Always broadcast the top-row selection so the parent screen knows
        # which meeting is active without requiring the user to press a key.
        self.post_message(self.MeetingSelected(meetings[0].id))

    # ------------------------------------------------------------------ #
    # Events
    # ------------------------------------------------------------------ #

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Fires as the cursor moves — gives immediate selection feedback."""
        if event.row_key and event.row_key.value:
            self.post_message(self.MeetingSelected(int(event.row_key.value)))
