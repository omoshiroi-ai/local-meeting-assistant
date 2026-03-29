"""Entrypoint for the local meeting assistant."""

import logging
from pathlib import Path

from src.config import DATA_DIR, FAISS_DIR
from src.db.connection import connect

LOG_PATH = Path("/tmp/meeting_assistant.log")


def _setup_logging() -> None:
    LOG_PATH.unlink(missing_ok=True)  # fresh log each run
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.FileHandler(LOG_PATH)],
    )


def _ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    FAISS_DIR.mkdir(parents=True, exist_ok=True)


def get_connection():
    """Return a configured SQLite connection (single-threaded TUI use)."""
    return connect(check_same_thread=True)


def _preinit_tqdm_lock() -> None:
    """Pre-initialize tqdm's multiprocessing lock on the main thread.

    mlx_whisper.transcribe() uses tqdm internally, which lazily creates a
    multiprocessing.RLock on first use.  That creation fails inside Textual's
    thread-pool executor because the resource tracker can't fork from there.
    Calling get_lock() here ensures the lock is created once on the main thread
    so worker threads just reuse it.
    """
    import tqdm
    tqdm.tqdm.get_lock()


def main() -> None:
    _setup_logging()
    _preinit_tqdm_lock()
    _ensure_dirs()
    from src.ui.app import MeetingAssistantApp

    app = MeetingAssistantApp()
    app.run()


if __name__ == "__main__":
    main()
