"""
Test Conversation Schema — Task 9

Validates patient_conversations table creation, indexes, TTL cleanup,
and migration compatibility.
"""

import sqlite3
import tempfile
import time
from datetime import datetime, timedelta
import pytest


@pytest.fixture
def db():
    """Create in-memory SQLite database for testing."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")

    # Load schema
    with open("schema/patient_conversations_table.sql") as f:
        conn.executescript(f.read())

    yield conn
    conn.close()


class TestConversationSchema:
    """Test table structure and indexes."""

    def test_schema_exists(self, db):
        """Verify patient_conversations table exists."""
        cursor = db.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='patient_conversations'"
        )
        result = cursor.fetchone()
        assert result is not None, "patient_conversations table not found"

    def test_columns_exist(self, db):
        """Verify all required columns exist."""
        cursor = db.cursor()
        cursor.execute("PRAGMA table_info(patient_conversations)")
        columns = {row[1] for row in cursor.fetchall()}

        required_columns = {
            'id', 'patient_id', 'message_id', 'sender', 'text',
            'timestamp', 'rag_confidence', 'escalated_flag', 'created_at'
        }

        assert required_columns.issubset(columns), (
            f"Missing columns: {required_columns - columns}"
        )

    def test_sender_check_constraint(self, db):
        """Verify sender CHECK constraint (only 'patient' or 'bot')."""
        cursor = db.cursor()

        # Valid values should work
        cursor.execute(
            "INSERT INTO patient_conversations (patient_id, sender, text) "
            "VALUES (?, ?, ?)",
            ("patient_123", "patient", "Hello")
        )
        db.commit()

        cursor.execute(
            "INSERT INTO patient_conversations (patient_id, sender, text) "
            "VALUES (?, ?, ?)",
            ("patient_123", "bot", "Hi there")
        )
        db.commit()

        # Invalid value should fail
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute(
                "INSERT INTO patient_conversations (patient_id, sender, text) "
                "VALUES (?, ?, ?)",
                ("patient_123", "invalid", "Bad sender")
            )
            db.commit()

    def test_message_id_uniqueness(self, db):
        """Verify message_id UNIQUE constraint."""
        cursor = db.cursor()

        cursor.execute(
            "INSERT INTO patient_conversations (patient_id, message_id, sender, text) "
            "VALUES (?, ?, ?, ?)",
            ("patient_123", "msg_001", "patient", "First message")
        )
        db.commit()

        # Duplicate message_id should fail
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute(
                "INSERT INTO patient_conversations (patient_id, message_id, sender, text) "
                "VALUES (?, ?, ?, ?)",
                ("patient_123", "msg_001", "bot", "Duplicate ID")
            )
            db.commit()

    def test_default_values(self, db):
        """Verify default values for timestamp, escalated_flag, rag_confidence."""
        cursor = db.cursor()

        cursor.execute(
            "INSERT INTO patient_conversations (patient_id, sender, text) "
            "VALUES (?, ?, ?)",
            ("patient_123", "patient", "Hello")
        )
        db.commit()

        cursor.execute("SELECT timestamp, escalated_flag, rag_confidence FROM patient_conversations LIMIT 1")
        row = cursor.fetchone()

        assert row[0] is not None, "timestamp should have default"
        assert row[1] == 0, "escalated_flag should default to 0"
        assert row[2] is None, "rag_confidence should default to NULL"


class TestIndexes:
    """Test that indexes exist and support efficient queries."""

    def test_patient_timestamp_index_exists(self, db):
        """Verify idx_patient_timestamp index exists."""
        cursor = db.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_patient_timestamp'"
        )
        assert cursor.fetchone() is not None, "idx_patient_timestamp not found"

    def test_timestamp_index_exists(self, db):
        """Verify idx_timestamp index exists."""
        cursor = db.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_timestamp'"
        )
        assert cursor.fetchone() is not None, "idx_timestamp not found"

    def test_escalated_flag_index_exists(self, db):
        """Verify idx_escalated_flag index exists."""
        cursor = db.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_escalated_flag'"
        )
        assert cursor.fetchone() is not None, "idx_escalated_flag not found"


class TestDataOperations:
    """Test basic CRUD operations."""

    def test_insert_message(self, db):
        """Verify messages can be inserted."""
        cursor = db.cursor()

        cursor.execute(
            "INSERT INTO patient_conversations "
            "(patient_id, message_id, sender, text, rag_confidence) "
            "VALUES (?, ?, ?, ?, ?)",
            ("patient_123", "msg_001", "patient", "What is diabetes?", None)
        )
        db.commit()

        cursor.execute(
            "SELECT COUNT(*) FROM patient_conversations WHERE patient_id = ?",
            ("patient_123",)
        )
        assert cursor.fetchone()[0] == 1

    def test_retrieve_conversation_history(self, db):
        """Verify conversation history can be retrieved by patient_id."""
        cursor = db.cursor()

        # Insert 5 messages
        messages = [
            ("patient_123", "msg_001", "patient", "Hello", None),
            ("patient_123", "msg_002", "bot", "Hi", 0.95),
            ("patient_123", "msg_003", "patient", "How are you?", None),
            ("patient_123", "msg_004", "bot", "I'm doing well", 0.88),
            ("patient_123", "msg_005", "patient", "Great!", None),
        ]

        for patient_id, msg_id, sender, text, conf in messages:
            cursor.execute(
                "INSERT INTO patient_conversations "
                "(patient_id, message_id, sender, text, rag_confidence) "
                "VALUES (?, ?, ?, ?, ?)",
                (patient_id, msg_id, sender, text, conf)
            )
        db.commit()

        # Retrieve all messages for patient
        cursor.execute(
            "SELECT * FROM patient_conversations WHERE patient_id = ? ORDER BY timestamp",
            ("patient_123",)
        )
        results = cursor.fetchall()
        assert len(results) == 5

    def test_update_escalated_flag(self, db):
        """Verify escalated_flag can be updated."""
        cursor = db.cursor()

        cursor.execute(
            "INSERT INTO patient_conversations "
            "(patient_id, message_id, sender, text, escalated_flag) "
            "VALUES (?, ?, ?, ?, ?)",
            ("patient_123", "msg_001", "patient", "Chest pain", 0)
        )
        db.commit()

        # Update escalated flag
        cursor.execute(
            "UPDATE patient_conversations SET escalated_flag = 1 WHERE message_id = ?",
            ("msg_001",)
        )
        db.commit()

        cursor.execute("SELECT escalated_flag FROM patient_conversations WHERE message_id = ?", ("msg_001",))
        assert cursor.fetchone()[0] == 1

    def test_delete_old_messages(self, db):
        """Verify old messages can be deleted (TTL cleanup)."""
        cursor = db.cursor()
        now = datetime.utcnow()

        # Insert current message
        cursor.execute(
            "INSERT INTO patient_conversations "
            "(patient_id, message_id, sender, text, timestamp) "
            "VALUES (?, ?, ?, ?, ?)",
            ("patient_123", "msg_new", "patient", "New message", now.isoformat())
        )

        # Insert old message (8 days ago)
        old_time = (now - timedelta(days=8)).isoformat()
        cursor.execute(
            "INSERT INTO patient_conversations "
            "(patient_id, message_id, sender, text, timestamp) "
            "VALUES (?, ?, ?, ?, ?)",
            ("patient_123", "msg_old", "patient", "Old message", old_time)
        )
        db.commit()

        # Verify both exist
        cursor.execute("SELECT COUNT(*) FROM patient_conversations WHERE patient_id = ?", ("patient_123",))
        assert cursor.fetchone()[0] == 2

        # Delete messages older than 7 days
        cutoff = (now - timedelta(days=7)).isoformat()
        cursor.execute(
            "DELETE FROM patient_conversations WHERE timestamp < ?",
            (cutoff,)
        )
        db.commit()

        # Verify old message deleted
        cursor.execute("SELECT COUNT(*) FROM patient_conversations WHERE patient_id = ?", ("patient_123",))
        assert cursor.fetchone()[0] == 1

        cursor.execute("SELECT message_id FROM patient_conversations WHERE patient_id = ?", ("patient_123",))
        assert cursor.fetchone()[0] == "msg_new"


class TestTTLCleanup:
    """Test TTL cleanup functionality."""

    def test_bulk_cleanup_with_ttl(self, db):
        """Verify cleanup removes >7-day-old rows efficiently."""
        cursor = db.cursor()
        now = datetime.utcnow()

        # Insert 100 messages: 70 recent, 30 old
        for i in range(100):
            if i < 70:
                ts = (now - timedelta(hours=i)).isoformat()
            else:
                ts = (now - timedelta(days=8 + (i - 70))).isoformat()

            cursor.execute(
                "INSERT INTO patient_conversations "
                "(patient_id, message_id, sender, text, timestamp) "
                "VALUES (?, ?, ?, ?, ?)",
                (f"patient_{i % 5}", f"msg_{i}", "patient" if i % 2 == 0 else "bot", f"Message {i}", ts)
            )
        db.commit()

        # Verify 100 messages exist
        cursor.execute("SELECT COUNT(*) FROM patient_conversations")
        assert cursor.fetchone()[0] == 100

        # Cleanup: delete messages older than 7 days
        cutoff = (now - timedelta(days=7)).isoformat()
        cursor.execute("DELETE FROM patient_conversations WHERE timestamp < ?", (cutoff,))
        db.commit()

        # Verify ~30 old messages deleted, ~70 remain
        cursor.execute("SELECT COUNT(*) FROM patient_conversations")
        remaining = cursor.fetchone()[0]
        assert 65 <= remaining <= 75, f"Expected ~70 messages remaining, got {remaining}"


class TestMigration:
    """Test schema migration compatibility."""

    def test_migration_adds_table_without_data_loss(self):
        """Verify migration can add table to existing clinic.db."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        # Create initial database (simulating existing clinic.db)
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE clinic_info (id INTEGER PRIMARY KEY, clinic_name TEXT)")
        conn.execute("INSERT INTO clinic_info (clinic_name) VALUES ('Test Clinic')")
        conn.commit()

        # Apply migration
        with open("schema/patient_conversations_table.sql") as f:
            conn.executescript(f.read())

        # Verify original table still exists and has data
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM clinic_info")
        assert cursor.fetchone()[0] == 1

        # Verify new table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='patient_conversations'")
        assert cursor.fetchone() is not None

        conn.close()

        import os
        os.unlink(db_path)
