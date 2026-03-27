"""TranscriptLog — auto-scrolling RichLog for live meeting transcription."""

from textual.widgets import RichLog


class TranscriptLog(RichLog):
    """RichLog subclass with meeting-specific helpers."""

    DEFAULT_CSS = """
    TranscriptLog {
        height: 1fr;
        padding: 1 2;
        border: blank;
        scrollbar-gutter: stable;
    }
    """

    def append_segment(self, text: str, timestamp_ms: int) -> None:
        """Write a transcription segment with a formatted timestamp prefix."""
        total_secs = timestamp_ms // 1000
        mins, secs = divmod(total_secs, 60)
        self.write(f"[dim]{mins:02d}:{secs:02d}[/dim]  {text}")
        self.scroll_end(animate=False)

    def append_status(self, message: str) -> None:
        """Write a dim status line (not a transcript segment)."""
        self.write(f"[dim italic]{message}[/dim italic]")
        self.scroll_end(animate=False)
