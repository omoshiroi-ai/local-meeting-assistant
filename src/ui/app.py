"""MeetingAssistantApp — root Textual application."""

from textual.app import App, ComposeResult

from src.config import DATA_DIR, FAISS_DIR
from src.db.migrations import run_migrations
from src.db.repository import AppStateRepo, ChatRepo, ChunkRepo, MeetingRepo, SegmentRepo
from src.db.schema import init_db
from src.main import get_connection


class MeetingAssistantApp(App):
    """Local meeting assistant: record, transcribe, and chat with your meetings."""

    TITLE = "Local Meeting Assistant"
    CSS = """
    Screen {
        background: $surface;
    }
    """

    ENABLE_COMMAND_PALETTE = False

    def __init__(self) -> None:
        super().__init__()

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        FAISS_DIR.mkdir(parents=True, exist_ok=True)

        self.conn = get_connection()
        init_db(self.conn)
        run_migrations(self.conn)

        self.meeting_repo = MeetingRepo(self.conn)
        self.segment_repo = SegmentRepo(self.conn)
        self.chunk_repo = ChunkRepo(self.conn)
        self.chat_repo = ChatRepo(self.conn)
        self.state_repo = AppStateRepo(self.conn)

    def on_mount(self) -> None:
        from src.ui.screens.home import HomeScreen

        self.push_screen(HomeScreen())

    def on_unmount(self) -> None:
        self.conn.close()

    def compose(self) -> ComposeResult:
        return iter([])
