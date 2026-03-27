"""ChatPanel — chat history + input widget for RAG Q&A."""

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, RichLog


class ChatPanel(Widget):
    """Vertical stack: scrollable message history on top, text input on bottom.

    Posts a ``ChatPanel.ChatSubmit`` message when the user submits a query.
    The parent screen is responsible for generating a response and calling
    ``add_message()`` / ``stream_token()`` back on this widget.
    """

    DEFAULT_CSS = """
    ChatPanel {
        width: 1fr;
        height: 1fr;
        layout: vertical;
    }

    ChatPanel #chat-log {
        height: 1fr;
        padding: 1 2;
        border: blank;
        scrollbar-gutter: stable;
    }

    ChatPanel #chat-input {
        height: 3;
        margin: 0 1 1 1;
        border: tall $primary;
    }
    """

    # ------------------------------------------------------------------ #
    # Messages
    # ------------------------------------------------------------------ #

    class ChatSubmit(Message):
        """Fired when the user submits a query."""

        def __init__(self, text: str) -> None:
            self.text = text
            super().__init__()

    # ------------------------------------------------------------------ #
    # Compose
    # ------------------------------------------------------------------ #

    def compose(self) -> ComposeResult:
        yield RichLog(id="chat-log", markup=True, highlight=False, wrap=True)
        yield Input(placeholder="Ask about this meeting…  (Enter to send)", id="chat-input")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def add_message(self, role: str, content: str) -> None:
        """Append a complete message to the chat history."""
        log = self.query_one(RichLog)
        if role == "user":
            log.write(f"[bold cyan]You[/bold cyan]  {content}")
        else:
            log.write(f"[bold green]Assistant[/bold green]  {content}")
        log.write("")  # blank line between turns
        log.scroll_end(animate=False)

    def begin_assistant_stream(self) -> None:
        """Start a new assistant turn that will be filled via stream_token()."""
        log = self.query_one(RichLog)
        log.write("[bold green]Assistant[/bold green]  ", end="")

    def stream_token(self, token: str) -> None:
        """Append a token to the current assistant turn (no newline)."""
        log = self.query_one(RichLog)
        log.write(token, end="")
        log.scroll_end(animate=False)

    def end_assistant_stream(self) -> None:
        """Close the current streaming turn with a trailing blank line."""
        log = self.query_one(RichLog)
        log.write("")
        log.write("")

    def focus_input(self) -> None:
        self.query_one(Input).focus()

    # ------------------------------------------------------------------ #
    # Events
    # ------------------------------------------------------------------ #

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if text:
            self.post_message(self.ChatSubmit(text))
            event.input.clear()
