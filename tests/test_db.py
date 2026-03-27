"""DB layer tests using in-memory SQLite."""

import json
import sqlite3

import pytest

from src.db.migrations import get_user_version, run_migrations
from src.db.repository import (
    AppStateRepo,
    ChatRepo,
    ChunkRepo,
    MeetingRepo,
    SegmentRepo,
)
from src.db.schema import init_db


@pytest.fixture
def conn():
    """Fresh in-memory SQLite connection for each test."""
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA foreign_keys=ON")
    init_db(c)
    run_migrations(c)
    yield c
    c.close()


# ---------------------------------------------------------------------------
# MeetingRepo
# ---------------------------------------------------------------------------


class TestMeetingRepo:
    def test_create_and_get(self, conn):
        repo = MeetingRepo(conn)
        mid = repo.create("Weekly Sync", source="zoom")
        assert mid == 1

        meeting = repo.get(mid)
        assert meeting is not None
        assert meeting.title == "Weekly Sync"
        assert meeting.source == "zoom"
        assert meeting.ended_at is None

    def test_end_meeting(self, conn):
        repo = MeetingRepo(conn)
        mid = repo.create()
        repo.end(mid)

        meeting = repo.get(mid)
        assert meeting.ended_at is not None

    def test_update_title(self, conn):
        repo = MeetingRepo(conn)
        mid = repo.create("Old Title")
        repo.update_title(mid, "New Title")
        assert repo.get(mid).title == "New Title"

    def test_update_notes(self, conn):
        repo = MeetingRepo(conn)
        mid = repo.create()
        repo.update_notes(mid, "Important action items")
        assert repo.get(mid).notes == "Important action items"

    def test_list_all_ordered_by_date(self, conn):
        repo = MeetingRepo(conn)
        repo.create("First")
        repo.create("Second")
        repo.create("Third")

        meetings = repo.list_all()
        assert len(meetings) == 3
        # Most recent first
        assert meetings[0].title == "Third"
        assert meetings[2].title == "First"

    def test_list_all_limit_offset(self, conn):
        repo = MeetingRepo(conn)
        for i in range(5):
            repo.create(f"Meeting {i}")

        page1 = repo.list_all(limit=2, offset=0)
        page2 = repo.list_all(limit=2, offset=2)
        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].id != page2[0].id

    def test_delete_cascades(self, conn):
        meeting_repo = MeetingRepo(conn)
        segment_repo = SegmentRepo(conn)

        mid = meeting_repo.create()
        segment_repo.insert(mid, 0, "Hello world", 0, 1000)
        assert segment_repo.count_by_meeting(mid) == 1

        meeting_repo.delete(mid)
        assert meeting_repo.get(mid) is None
        assert segment_repo.count_by_meeting(mid) == 0

    def test_get_nonexistent_returns_none(self, conn):
        assert MeetingRepo(conn).get(9999) is None

    def test_count(self, conn):
        repo = MeetingRepo(conn)
        assert repo.count() == 0
        repo.create()
        repo.create()
        assert repo.count() == 2


# ---------------------------------------------------------------------------
# SegmentRepo
# ---------------------------------------------------------------------------


class TestSegmentRepo:
    def test_insert_and_retrieve(self, conn):
        mid = MeetingRepo(conn).create()
        repo = SegmentRepo(conn)

        repo.insert(mid, 0, "Hello world", 0, 1500, confidence=0.95)
        repo.insert(mid, 1, "How are you", 1500, 3000)

        segments = repo.get_by_meeting(mid)
        assert len(segments) == 2
        assert segments[0].text == "Hello world"
        assert segments[0].confidence == pytest.approx(0.95)
        assert segments[1].sequence_num == 1

    def test_next_sequence_num_empty(self, conn):
        mid = MeetingRepo(conn).create()
        assert SegmentRepo(conn).next_sequence_num(mid) == 0

    def test_next_sequence_num_after_inserts(self, conn):
        mid = MeetingRepo(conn).create()
        repo = SegmentRepo(conn)
        repo.insert(mid, 0, "First", 0, 500)
        repo.insert(mid, 1, "Second", 500, 1000)
        assert repo.next_sequence_num(mid) == 2

    def test_segments_ordered_by_sequence(self, conn):
        mid = MeetingRepo(conn).create()
        repo = SegmentRepo(conn)
        repo.insert(mid, 2, "Third", 2000, 3000)
        repo.insert(mid, 0, "First", 0, 1000)
        repo.insert(mid, 1, "Second", 1000, 2000)

        segments = repo.get_by_meeting(mid)
        assert [s.sequence_num for s in segments] == [0, 1, 2]

    def test_count_by_meeting(self, conn):
        mid = MeetingRepo(conn).create()
        repo = SegmentRepo(conn)
        assert repo.count_by_meeting(mid) == 0
        repo.insert(mid, 0, "Hi", 0, 500)
        assert repo.count_by_meeting(mid) == 1


# ---------------------------------------------------------------------------
# ChunkRepo
# ---------------------------------------------------------------------------


class TestChunkRepo:
    def _make_chunks(self, meeting_id: int, n: int = 3) -> list[dict]:
        return [
            {
                "meeting_id": meeting_id,
                "chunk_index": i,
                "text": f"Chunk {i} text content",
                "start_ms": i * 10000,
                "end_ms": (i + 1) * 10000,
                "token_count": 50,
            }
            for i in range(n)
        ]

    def test_insert_many_and_get_by_meeting(self, conn):
        mid = MeetingRepo(conn).create()
        repo = ChunkRepo(conn)

        ids = repo.insert_many(self._make_chunks(mid))
        assert len(ids) == 3

        chunks = repo.get_by_meeting(mid)
        assert len(chunks) == 3
        assert chunks[0].chunk_index == 0
        assert chunks[0].indexed_at is None

    def test_get_by_ids(self, conn):
        mid = MeetingRepo(conn).create()
        repo = ChunkRepo(conn)
        ids = repo.insert_many(self._make_chunks(mid, n=2))

        result = repo.get_by_ids([ids[0]])
        assert len(result) == 1
        assert result[0].id == ids[0]

    def test_get_by_ids_empty(self, conn):
        assert ChunkRepo(conn).get_by_ids([]) == []

    def test_update_faiss_row_ids(self, conn):
        mid = MeetingRepo(conn).create()
        repo = ChunkRepo(conn)
        ids = repo.insert_many(self._make_chunks(mid, n=2))

        repo.update_faiss_row_ids({ids[0]: 100, ids[1]: 101})

        chunks = repo.get_by_meeting(mid)
        assert chunks[0].faiss_row_id == 100
        assert chunks[1].faiss_row_id == 101
        assert chunks[0].indexed_at is not None

    def test_delete_by_meeting(self, conn):
        mid = MeetingRepo(conn).create()
        repo = ChunkRepo(conn)
        repo.insert_many(self._make_chunks(mid))
        assert len(repo.get_by_meeting(mid)) == 3

        repo.delete_by_meeting(mid)
        assert repo.get_by_meeting(mid) == []

    def test_get_unindexed(self, conn):
        mid = MeetingRepo(conn).create()
        repo = ChunkRepo(conn)
        ids = repo.insert_many(self._make_chunks(mid, n=3))

        # Mark one as indexed
        repo.update_faiss_row_ids({ids[0]: 0})

        unindexed = repo.get_unindexed()
        assert len(unindexed) == 2
        assert all(c.indexed_at is None for c in unindexed)


# ---------------------------------------------------------------------------
# ChatRepo
# ---------------------------------------------------------------------------


class TestChatRepo:
    def test_create_session_and_add_messages(self, conn):
        mid = MeetingRepo(conn).create()
        repo = ChatRepo(conn)

        sid = repo.create_session(meeting_id=mid)
        assert sid == 1

        repo.add_message(sid, "user", "What was discussed?", retrieved_chunk_ids=[1, 2])
        repo.add_message(sid, "assistant", "The team discussed Q1 goals.")

        messages = repo.get_messages(sid)
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].retrieved_chunk_ids == [1, 2]
        assert messages[1].role == "assistant"
        assert messages[1].retrieved_chunk_ids == []

    def test_end_session(self, conn):
        repo = ChatRepo(conn)
        sid = repo.create_session()
        assert repo.get_session(sid).ended_at is None

        repo.end_session(sid)
        assert repo.get_session(sid).ended_at is not None

    def test_cross_meeting_session(self, conn):
        repo = ChatRepo(conn)
        sid = repo.create_session(meeting_id=None)
        session = repo.get_session(sid)
        assert session.meeting_id is None

    def test_get_session_nonexistent(self, conn):
        assert ChatRepo(conn).get_session(9999) is None


# ---------------------------------------------------------------------------
# AppStateRepo
# ---------------------------------------------------------------------------


class TestAppStateRepo:
    def test_set_and_get(self, conn):
        repo = AppStateRepo(conn)
        repo.set("last_meeting_id", "42")
        assert repo.get("last_meeting_id") == "42"

    def test_get_default(self, conn):
        repo = AppStateRepo(conn)
        assert repo.get("missing_key") is None
        assert repo.get("missing_key", "fallback") == "fallback"

    def test_upsert(self, conn):
        repo = AppStateRepo(conn)
        repo.set("key", "first")
        repo.set("key", "second")
        assert repo.get("key") == "second"

    def test_delete(self, conn):
        repo = AppStateRepo(conn)
        repo.set("temp", "value")
        repo.delete("temp")
        assert repo.get("temp") is None


# ---------------------------------------------------------------------------
# Migrations
# ---------------------------------------------------------------------------


class TestMigrations:
    def test_initial_version_is_zero(self, conn):
        # After init_db + run_migrations with no pending migrations, version stays 0
        assert get_user_version(conn) == 0

    def test_run_migrations_idempotent(self, conn):
        # Running again should not raise or change state
        run_migrations(conn)
        run_migrations(conn)
        assert get_user_version(conn) == 0
