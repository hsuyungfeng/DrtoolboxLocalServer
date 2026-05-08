"""
Test Conversation Manager Service — Task 10

Validates CRUD operations, thread-safety, performance, and error handling.
"""

import sqlite3
import threading
import time
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

# ── Path setup ─────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from services.conversation_manager import ConversationManager, Message


@pytest.fixture
def db():
    """Create in-memory database with schema for testing."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")

    with open("schema/patient_conversations_table.sql") as f:
        conn.executescript(f.read())

    yield conn
    conn.close()


@pytest.fixture
def manager(db):
    """Create ConversationManager with in-memory database."""
    mgr = ConversationManager(":memory:")

    # Manually initialize the in-memory DB with schema
    conn = mgr._get_connection()
    with open("schema/patient_conversations_table.sql") as f:
        conn.executescript(f.read())

    yield mgr
    mgr.close()


class TestMessageClass:
    """Test Message data class."""

    def test_message_creation(self):
        """Verify Message can be created."""
        msg = Message(
            message_id="msg_001",
            patient_id="patient_123",
            sender="patient",
            text="Hello",
            timestamp="2026-05-08T10:00:00Z",
            rag_confidence=None,
            escalated_flag=False,
        )

        assert msg.message_id == "msg_001"
        assert msg.patient_id == "patient_123"
        assert msg.sender == "patient"

    def test_message_to_dict(self):
        """Verify Message.to_dict() works."""
        msg = Message(
            message_id="msg_001",
            patient_id="patient_123",
            sender="bot",
            text="Hi there",
            timestamp="2026-05-08T10:00:05Z",
            rag_confidence=0.95,
            escalated_flag=False,
        )

        d = msg.to_dict()
        assert d["message_id"] == "msg_001"
        assert d["rag_confidence"] == 0.95
        assert d["sender"] == "bot"


class TestSaveMessage:
    """Test save_message() operation."""

    def test_save_message_success(self, manager):
        """Verify message can be saved."""
        msg_id = manager.save_message(
            patient_id="patient_123",
            sender="patient",
            text="What is diabetes?",
        )

        assert msg_id is not None
        assert isinstance(msg_id, str)
        assert len(msg_id) > 0

    def test_save_message_with_rag_confidence(self, manager):
        """Verify message with RAG confidence can be saved."""
        msg_id = manager.save_message(
            patient_id="patient_123",
            sender="bot",
            text="Diabetes is...",
            rag_confidence=0.95,
        )

        assert msg_id is not None

        # Retrieve and verify
        msg = manager.get_message_by_id(msg_id)
        assert msg.rag_confidence == 0.95

    def test_save_message_escalated(self, manager):
        """Verify escalated message can be saved."""
        msg_id = manager.save_message(
            patient_id="patient_123",
            sender="patient",
            text="Emergency!",
            escalated=True,
        )

        msg = manager.get_message_by_id(msg_id)
        assert msg.escalated_flag is True

    def test_save_message_invalid_patient_id(self, manager):
        """Verify invalid patient_id raises ValueError."""
        with pytest.raises(ValueError):
            manager.save_message(
                patient_id="",
                sender="patient",
                text="Hello",
            )

        with pytest.raises(ValueError):
            manager.save_message(
                patient_id=None,
                sender="patient",
                text="Hello",
            )

    def test_save_message_invalid_sender(self, manager):
        """Verify invalid sender raises ValueError."""
        with pytest.raises(ValueError):
            manager.save_message(
                patient_id="patient_123",
                sender="invalid",
                text="Hello",
            )

    def test_save_message_invalid_rag_confidence(self, manager):
        """Verify invalid rag_confidence raises ValueError."""
        with pytest.raises(ValueError):
            manager.save_message(
                patient_id="patient_123",
                sender="bot",
                text="Hello",
                rag_confidence=1.5,  # > 1.0
            )

        with pytest.raises(ValueError):
            manager.save_message(
                patient_id="patient_123",
                sender="bot",
                text="Hello",
                rag_confidence=-0.1,  # < 0.0
            )

    def test_save_message_empty_text(self, manager):
        """Verify empty text raises ValueError."""
        with pytest.raises(ValueError):
            manager.save_message(
                patient_id="patient_123",
                sender="patient",
                text="",
            )


class TestGetHistory:
    """Test get_conversation_history() operation."""

    def test_get_history_empty(self, manager):
        """Verify empty history returns empty list."""
        history = manager.get_conversation_history("patient_999")
        assert history == []

    def test_get_history_single_message(self, manager):
        """Verify single message history."""
        msg_id = manager.save_message(
            patient_id="patient_123",
            sender="patient",
            text="Hello",
        )

        history = manager.get_conversation_history("patient_123")
        assert len(history) == 1
        assert history[0].message_id == msg_id

    def test_get_history_multiple_messages(self, manager):
        """Verify multiple messages in correct order."""
        ids = []
        for i in range(5):
            msg_id = manager.save_message(
                patient_id="patient_123",
                sender="patient" if i % 2 == 0 else "bot",
                text=f"Message {i}",
            )
            ids.append(msg_id)

        history = manager.get_conversation_history("patient_123")
        assert len(history) == 5

        # Verify order (oldest first)
        for i, msg in enumerate(history):
            assert msg.message_id == ids[i]

    def test_get_history_only_returns_specified_patient(self, manager):
        """Verify history only returns messages for specified patient."""
        manager.save_message("patient_123", "patient", "Patient 123 message")
        manager.save_message("patient_456", "patient", "Patient 456 message")

        history_123 = manager.get_conversation_history("patient_123")
        history_456 = manager.get_conversation_history("patient_456")

        assert len(history_123) == 1
        assert len(history_456) == 1
        assert history_123[0].patient_id == "patient_123"
        assert history_456[0].patient_id == "patient_456"

    def test_get_history_respects_day_filter(self, manager):
        """Verify history respects days parameter."""
        now = datetime.utcnow()

        # Insert current message
        manager.save_message("patient_123", "patient", "Recent message")

        # Insert old message (manually in DB to bypass manager's timestamp)
        conn = manager._get_connection()
        old_time = (now - timedelta(days=8)).isoformat() + "Z"
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO patient_conversations "
            "(patient_id, sender, text, timestamp) VALUES (?, ?, ?, ?)",
            ("patient_123", "patient", "Old message", old_time),
        )
        conn.commit()

        # Get history with 7-day filter (should exclude old message)
        history = manager.get_conversation_history("patient_123", days=7)
        assert len(history) == 1
        assert history[0].text == "Recent message"

        # Get history with 10-day filter (should include both)
        history = manager.get_conversation_history("patient_123", days=10)
        assert len(history) == 2

    def test_get_history_invalid_patient_id(self, manager):
        """Verify invalid patient_id raises ValueError."""
        with pytest.raises(ValueError):
            manager.get_conversation_history("")

        with pytest.raises(ValueError):
            manager.get_conversation_history(None)


class TestCleanupOldConversations:
    """Test cleanup_old_conversations() operation."""

    def test_cleanup_removes_old_messages(self, manager):
        """Verify cleanup removes messages older than TTL."""
        now = datetime.utcnow()

        # Insert recent and old messages directly
        conn = manager._get_connection()
        cursor = conn.cursor()

        # Recent message
        recent_time = now.isoformat() + "Z"
        cursor.execute(
            "INSERT INTO patient_conversations "
            "(patient_id, sender, text, timestamp) VALUES (?, ?, ?, ?)",
            ("patient_123", "patient", "Recent", recent_time),
        )

        # Old message (8 days ago)
        old_time = (now - timedelta(days=8)).isoformat() + "Z"
        cursor.execute(
            "INSERT INTO patient_conversations "
            "(patient_id, sender, text, timestamp) VALUES (?, ?, ?, ?)",
            ("patient_123", "patient", "Old", old_time),
        )
        conn.commit()

        # Verify both exist
        cursor.execute("SELECT COUNT(*) FROM patient_conversations WHERE patient_id = ?", ("patient_123",))
        assert cursor.fetchone()[0] == 2

        # Cleanup
        deleted = manager.cleanup_old_conversations(days=7)
        assert deleted == 1

        # Verify old message deleted
        cursor.execute("SELECT COUNT(*) FROM patient_conversations WHERE patient_id = ?", ("patient_123",))
        assert cursor.fetchone()[0] == 1

    def test_cleanup_bulk_operation(self, manager):
        """Verify cleanup performs efficiently on bulk data."""
        now = datetime.utcnow()
        conn = manager._get_connection()
        cursor = conn.cursor()

        # Insert 100 messages: 70 recent, 30 old
        for i in range(100):
            if i < 70:
                ts = (now - timedelta(hours=i)).isoformat() + "Z"
            else:
                ts = (now - timedelta(days=8 + (i - 70))).isoformat() + "Z"

            cursor.execute(
                "INSERT INTO patient_conversations "
                "(patient_id, sender, text, timestamp) VALUES (?, ?, ?, ?)",
                (f"patient_{i % 5}", "patient", f"Message {i}", ts),
            )
        conn.commit()

        # Cleanup
        deleted = manager.cleanup_old_conversations(days=7)
        assert 25 <= deleted <= 35  # ~30 old messages

        # Verify remaining count
        cursor.execute("SELECT COUNT(*) FROM patient_conversations")
        remaining = cursor.fetchone()[0]
        assert 65 <= remaining <= 75


class TestGetMessageById:
    """Test get_message_by_id() operation."""

    def test_get_message_by_id_success(self, manager):
        """Verify message can be retrieved by ID."""
        msg_id = manager.save_message("patient_123", "patient", "Hello")

        msg = manager.get_message_by_id(msg_id)
        assert msg is not None
        assert msg.message_id == msg_id
        assert msg.text == "Hello"

    def test_get_message_by_id_not_found(self, manager):
        """Verify None returned for non-existent message."""
        msg = manager.get_message_by_id("non_existent_id")
        assert msg is None

    def test_get_message_by_id_invalid_input(self, manager):
        """Verify invalid message_id raises ValueError."""
        with pytest.raises(ValueError):
            manager.get_message_by_id("")

        with pytest.raises(ValueError):
            manager.get_message_by_id(None)


class TestMarkEscalated:
    """Test mark_escalated() operation."""

    def test_mark_escalated_success(self, manager):
        """Verify message can be marked as escalated."""
        msg_id = manager.save_message("patient_123", "patient", "Help!", escalated=False)

        result = manager.mark_escalated(msg_id)
        assert result is True

        msg = manager.get_message_by_id(msg_id)
        assert msg.escalated_flag is True

    def test_mark_escalated_not_found(self, manager):
        """Verify mark_escalated returns False for non-existent message."""
        result = manager.mark_escalated("non_existent_id")
        assert result is False

    def test_mark_escalated_invalid_input(self, manager):
        """Verify invalid message_id raises ValueError."""
        with pytest.raises(ValueError):
            manager.mark_escalated("")

        with pytest.raises(ValueError):
            manager.mark_escalated(None)


class TestGetEscalatedMessages:
    """Test get_escalated_messages() operation."""

    def test_get_escalated_messages(self, manager):
        """Verify escalated messages can be retrieved."""
        msg_id_1 = manager.save_message("patient_123", "patient", "Help!", escalated=True)
        msg_id_2 = manager.save_message("patient_123", "patient", "Normal message", escalated=False)

        escalated = manager.get_escalated_messages("patient_123")
        assert len(escalated) == 1
        assert escalated[0].message_id == msg_id_1

    def test_get_escalated_messages_empty(self, manager):
        """Verify empty list returned when no escalated messages."""
        manager.save_message("patient_123", "patient", "Normal message", escalated=False)

        escalated = manager.get_escalated_messages("patient_123")
        assert escalated == []

    def test_get_escalated_messages_respects_days(self, manager):
        """Verify escalated messages respect days filter."""
        now = datetime.utcnow()
        conn = manager._get_connection()
        cursor = conn.cursor()

        # Recent escalated message
        manager.save_message("patient_123", "patient", "Recent escalation", escalated=True)

        # Old escalated message (8 days ago)
        old_time = (now - timedelta(days=8)).isoformat() + "Z"
        cursor.execute(
            "INSERT INTO patient_conversations "
            "(patient_id, sender, text, escalated_flag, timestamp) "
            "VALUES (?, ?, ?, ?, ?)",
            ("patient_123", "patient", "Old escalation", 1, old_time),
        )
        conn.commit()

        # Get with 7-day filter (should exclude old)
        escalated = manager.get_escalated_messages("patient_123", days=7)
        assert len(escalated) == 1

        # Get with 10-day filter (should include both)
        escalated = manager.get_escalated_messages("patient_123", days=10)
        assert len(escalated) == 2


class TestConcurrency:
    """Test thread-safety of ConversationManager."""

    def test_concurrent_writes(self, manager):
        """Verify concurrent writes don't cause data loss or corruption."""
        num_threads = 10
        messages_per_thread = 10

        def writer(thread_id):
            for i in range(messages_per_thread):
                manager.save_message(
                    patient_id=f"patient_{thread_id}",
                    sender="patient" if i % 2 == 0 else "bot",
                    text=f"Thread {thread_id} Message {i}",
                )

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(num_threads)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Verify all messages saved
        total_expected = num_threads * messages_per_thread
        conn = manager._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM patient_conversations")
        total_saved = cursor.fetchone()[0]

        assert total_saved == total_expected

    def test_concurrent_reads_writes(self, manager):
        """Verify concurrent reads and writes are safe."""
        num_writers = 5
        num_readers = 5
        messages_per_writer = 5

        results = {"read_count": 0, "lock": threading.Lock()}

        def writer(thread_id):
            for i in range(messages_per_writer):
                manager.save_message(
                    patient_id=f"patient_{thread_id}",
                    sender="patient",
                    text=f"Message {i}",
                )
                time.sleep(0.01)

        def reader(thread_id):
            # Try to read every patient
            for p_id in range(num_writers):
                history = manager.get_conversation_history(f"patient_{p_id}")
                with results["lock"]:
                    results["read_count"] += 1

        writer_threads = [threading.Thread(target=writer, args=(i,)) for i in range(num_writers)]
        reader_threads = [threading.Thread(target=reader, args=(i,)) for i in range(num_readers)]

        all_threads = writer_threads + reader_threads
        for t in all_threads:
            t.start()

        for t in all_threads:
            t.join()

        # Verify reads completed without error
        assert results["read_count"] > 0


class TestPerformance:
    """Test performance guarantees."""

    def test_get_history_performance(self, manager):
        """Verify get_conversation_history < 200ms."""
        # Insert 100 messages
        for i in range(100):
            manager.save_message(
                patient_id="patient_123",
                sender="patient" if i % 2 == 0 else "bot",
                text=f"Message {i}",
            )

        # Measure retrieval time
        start = time.time()
        history = manager.get_conversation_history("patient_123")
        elapsed = (time.time() - start) * 1000  # ms

        assert len(history) == 100
        assert elapsed < 200, f"get_history took {elapsed:.1f}ms (target: <200ms)"

    def test_save_message_performance(self, manager):
        """Verify save_message is reasonably fast."""
        start = time.time()
        for i in range(100):
            manager.save_message(
                patient_id="patient_123",
                sender="patient" if i % 2 == 0 else "bot",
                text=f"Message {i}",
            )
        elapsed = (time.time() - start) * 1000  # ms

        # 100 messages should complete in < 5 seconds
        assert elapsed < 5000, f"100 saves took {elapsed:.1f}ms (target: <5000ms)"
