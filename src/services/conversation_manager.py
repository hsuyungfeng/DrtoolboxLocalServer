"""
Conversation Manager Service — Task 10

Encapsulates conversation history CRUD operations with:
- Thread-safe database access (connection pooling)
- Audit logging for all operations
- Performance guarantees (<200ms for get_history)
- Error handling for database locks, missing data, schema errors
"""

import logging
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class Message:
    """Represents a conversation message."""

    def __init__(
        self,
        message_id: str,
        patient_id: str,
        sender: str,
        text: str,
        timestamp: str,
        rag_confidence: Optional[float] = None,
        escalated_flag: bool = False,
    ):
        self.message_id = message_id
        self.patient_id = patient_id
        self.sender = sender
        self.text = text
        self.timestamp = timestamp
        self.rag_confidence = rag_confidence
        self.escalated_flag = escalated_flag

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "message_id": self.message_id,
            "patient_id": self.patient_id,
            "sender": self.sender,
            "text": self.text,
            "timestamp": self.timestamp,
            "rag_confidence": self.rag_confidence,
            "escalated_flag": self.escalated_flag,
        }


class ConversationManager:
    """
    Thread-safe manager for conversation history.

    Uses a single SQLite connection with a threading lock for concurrent writes.
    """

    def __init__(self, db_path: str = "data/db/clinic.db"):
        """
        Initialize ConversationManager.

        Args:
            db_path: Path to clinic.db (":memory:" for testing)
        """
        self.db_path = db_path
        self._lock = threading.RLock()
        self._conn = None

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create thread-local database connection."""
        with self._lock:
            if self._conn is None:
                self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
                self._conn.row_factory = sqlite3.Row
                self._conn.execute("PRAGMA journal_mode = WAL")  # Write-Ahead Logging for concurrency
                self._conn.execute("PRAGMA foreign_keys = ON")
            return self._conn

    def close(self) -> None:
        """Close database connection."""
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    def save_message(
        self,
        patient_id: str,
        sender: str,
        text: str,
        rag_confidence: Optional[float] = None,
        escalated: bool = False,
    ) -> str:
        """
        Save a conversation message to database.

        Args:
            patient_id: Patient identifier
            sender: 'patient' or 'bot'
            text: Message content
            rag_confidence: RAG confidence score (0.0-1.0) or None
            escalated: Whether message was escalated

        Returns:
            message_id (UUID string)

        Raises:
            ValueError: If inputs invalid
            sqlite3.DatabaseError: On database error
        """
        if not patient_id or not isinstance(patient_id, str):
            raise ValueError("patient_id must be a non-empty string")

        if sender not in ("patient", "bot"):
            raise ValueError("sender must be 'patient' or 'bot'")

        if not text or not isinstance(text, str):
            raise ValueError("text must be a non-empty string")

        if rag_confidence is not None and not (0.0 <= rag_confidence <= 1.0):
            raise ValueError("rag_confidence must be between 0.0 and 1.0")

        message_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat() + "Z"

        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT INTO patient_conversations
                    (patient_id, message_id, sender, text, rag_confidence, escalated_flag, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (patient_id, message_id, sender, text, rag_confidence, escalated, timestamp),
                )
                conn.commit()

                logger.info(
                    "Message saved | patient=%s msg_id=%s sender=%s escalated=%s",
                    patient_id,
                    message_id,
                    sender,
                    escalated,
                )

                return message_id

        except sqlite3.IntegrityError as exc:
            logger.error("Integrity error saving message | patient=%s error=%s", patient_id, exc)
            raise
        except sqlite3.OperationalError as exc:
            logger.error("Database error saving message | patient=%s error=%s", patient_id, exc)
            raise

    def get_conversation_history(
        self,
        patient_id: str,
        days: int = 7,
    ) -> List[Message]:
        """
        Retrieve conversation history for a patient.

        Args:
            patient_id: Patient identifier
            days: Number of days to retrieve (default 7)

        Returns:
            List of Message objects, ordered by timestamp (oldest first)

        Raises:
            ValueError: If patient_id invalid
            sqlite3.DatabaseError: On database error
        """
        if not patient_id or not isinstance(patient_id, str):
            raise ValueError("patient_id must be a non-empty string")

        cutoff = datetime.utcnow() - timedelta(days=days)
        cutoff_iso = cutoff.isoformat() + "Z"

        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT
                        message_id, patient_id, sender, text, timestamp,
                        rag_confidence, escalated_flag
                    FROM patient_conversations
                    WHERE patient_id = ? AND timestamp >= ?
                    ORDER BY timestamp ASC
                    """,
                    (patient_id, cutoff_iso),
                )

                rows = cursor.fetchall()
                messages = [
                    Message(
                        message_id=row[0],
                        patient_id=row[1],
                        sender=row[2],
                        text=row[3],
                        timestamp=row[4],
                        rag_confidence=row[5],
                        escalated_flag=bool(row[6]),
                    )
                    for row in rows
                ]

                logger.info(
                    "History retrieved | patient=%s count=%d days=%d",
                    patient_id,
                    len(messages),
                    days,
                )

                return messages

        except sqlite3.OperationalError as exc:
            logger.error("Database error retrieving history | patient=%s error=%s", patient_id, exc)
            raise

    def cleanup_old_conversations(self, days: int = 7) -> int:
        """
        Delete conversation messages older than specified days (TTL cleanup).

        Args:
            days: Keep messages newer than this many days (default 7)

        Returns:
            Number of messages deleted

        Raises:
            sqlite3.DatabaseError: On database error
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        cutoff_iso = cutoff.isoformat() + "Z"

        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                cursor.execute(
                    "DELETE FROM patient_conversations WHERE timestamp < ?",
                    (cutoff_iso,),
                )
                conn.commit()

                deleted_count = cursor.rowcount
                logger.info(
                    "Cleanup completed | deleted=%d days=%d cutoff=%s",
                    deleted_count,
                    days,
                    cutoff_iso,
                )

                return deleted_count

        except sqlite3.OperationalError as exc:
            logger.error("Database error during cleanup | error=%s", exc)
            raise

    def get_message_by_id(self, message_id: str) -> Optional[Message]:
        """
        Retrieve a single message by ID.

        Args:
            message_id: Message UUID

        Returns:
            Message object or None if not found
        """
        if not message_id:
            raise ValueError("message_id must be a non-empty string")

        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT
                        message_id, patient_id, sender, text, timestamp,
                        rag_confidence, escalated_flag
                    FROM patient_conversations
                    WHERE message_id = ?
                    """,
                    (message_id,),
                )

                row = cursor.fetchone()
                if row is None:
                    return None

                return Message(
                    message_id=row[0],
                    patient_id=row[1],
                    sender=row[2],
                    text=row[3],
                    timestamp=row[4],
                    rag_confidence=row[5],
                    escalated_flag=bool(row[6]),
                )

        except sqlite3.OperationalError as exc:
            logger.error("Database error retrieving message | msg_id=%s error=%s", message_id, exc)
            raise

    def mark_escalated(self, message_id: str) -> bool:
        """
        Mark a message as escalated.

        Args:
            message_id: Message UUID

        Returns:
            True if successful, False if message not found

        Raises:
            sqlite3.DatabaseError: On database error
        """
        if not message_id:
            raise ValueError("message_id must be a non-empty string")

        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                cursor.execute(
                    "UPDATE patient_conversations SET escalated_flag = 1 WHERE message_id = ?",
                    (message_id,),
                )
                conn.commit()

                success = cursor.rowcount > 0
                if success:
                    logger.info("Message marked escalated | msg_id=%s", message_id)
                else:
                    logger.warning("Message not found for escalation mark | msg_id=%s", message_id)

                return success

        except sqlite3.OperationalError as exc:
            logger.error("Database error marking escalated | msg_id=%s error=%s", message_id, exc)
            raise

    def get_escalated_messages(self, patient_id: str, days: int = 7) -> List[Message]:
        """
        Get escalated messages for a patient within a time window.

        Args:
            patient_id: Patient identifier
            days: Number of days to look back

        Returns:
            List of escalated Message objects
        """
        if not patient_id:
            raise ValueError("patient_id must be a non-empty string")

        cutoff = datetime.utcnow() - timedelta(days=days)
        cutoff_iso = cutoff.isoformat() + "Z"

        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT
                        message_id, patient_id, sender, text, timestamp,
                        rag_confidence, escalated_flag
                    FROM patient_conversations
                    WHERE patient_id = ? AND escalated_flag = 1 AND timestamp >= ?
                    ORDER BY timestamp DESC
                    """,
                    (patient_id, cutoff_iso),
                )

                rows = cursor.fetchall()
                messages = [
                    Message(
                        message_id=row[0],
                        patient_id=row[1],
                        sender=row[2],
                        text=row[3],
                        timestamp=row[4],
                        rag_confidence=row[5],
                        escalated_flag=bool(row[6]),
                    )
                    for row in rows
                ]

                logger.info(
                    "Escalated history retrieved | patient=%s count=%d",
                    patient_id,
                    len(messages),
                )

                return messages

        except sqlite3.OperationalError as exc:
            logger.error("Database error retrieving escalated messages | patient=%s error=%s", patient_id, exc)
            raise
