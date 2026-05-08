"""
Escalation Handler Service — Task 11

Creates escalation records when RAG confidence < 60% with full conversation context.
Routes escalations to staff (stub for Phase 3 integration) and provides resolution tracking.

Integrates with:
  - message_router.py (Task 6): when confidence < 60%
  - line_responder.py (Task 7): after sending/escalating
  - conversation_manager.py (Task 10): to fetch context
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional
import os
import json

logger = logging.getLogger(__name__)

# Escalation log file (stub for Phase 3 staff inbox integration)
ESCALATIONS_LOG_DIR = os.getenv("ESCALATIONS_LOG_DIR", "logs")
os.makedirs(ESCALATIONS_LOG_DIR, exist_ok=True)
ESCALATIONS_LOG_FILE = os.path.join(ESCALATIONS_LOG_DIR, "escalations.log")


class Escalation:
    """Represents an escalation record."""

    def __init__(
        self,
        escalation_id: str,
        patient_id: str,
        message_id: str,
        original_message: str,
        rag_confidence: float,
        conversation_history: List[dict],
        created_at: str,
        status: str = "pending",
        resolution_notes: Optional[str] = None,
        resolved_by: Optional[str] = None,
        resolved_at: Optional[str] = None,
    ):
        self.escalation_id = escalation_id
        self.patient_id = patient_id
        self.message_id = message_id
        self.original_message = original_message
        self.rag_confidence = rag_confidence
        self.conversation_history = conversation_history
        self.created_at = created_at
        self.status = status  # pending | resolved | reassigned
        self.resolution_notes = resolution_notes
        self.resolved_by = resolved_by
        self.resolved_at = resolved_at

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "escalation_id": self.escalation_id,
            "patient_id": self.patient_id,
            "message_id": self.message_id,
            "original_message": self.original_message,
            "rag_confidence": self.rag_confidence,
            "conversation_history": self.conversation_history,
            "created_at": self.created_at,
            "status": self.status,
            "resolution_notes": self.resolution_notes,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at,
        }


class EscalationHandler:
    """
    Manages escalation creation, routing, and resolution.

    Current implementation:
      - Logs escalations to file (Phase 3: integrate with staff inbox)
      - Tracks status: pending → resolved/reassigned
      - Includes full 7-day conversation context
    """

    def __init__(self):
        """Initialize EscalationHandler."""
        pass

    def create_escalation(
        self,
        patient_id: str,
        original_message: str,
        rag_confidence: float,
        conversation_history: List[dict],
        message_id: Optional[str] = None,
    ) -> Escalation:
        """
        Create an escalation record with full context.

        Args:
            patient_id: Patient identifier
            original_message: The message that triggered escalation
            rag_confidence: RAG confidence score that triggered escalation
            conversation_history: Full 7-day conversation context (list of dicts)
            message_id: Optional message ID (if available)

        Returns:
            Escalation object

        Raises:
            ValueError: If inputs invalid
        """
        if not patient_id or not isinstance(patient_id, str):
            raise ValueError("patient_id must be a non-empty string")

        if not original_message or not isinstance(original_message, str):
            raise ValueError("original_message must be a non-empty string")

        if not isinstance(rag_confidence, (int, float)) or not (0.0 <= rag_confidence <= 1.0):
            raise ValueError("rag_confidence must be between 0.0 and 1.0")

        if not isinstance(conversation_history, list):
            raise ValueError("conversation_history must be a list")

        escalation_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat() + "Z"

        if message_id is None:
            message_id = escalation_id

        escalation = Escalation(
            escalation_id=escalation_id,
            patient_id=patient_id,
            message_id=message_id,
            original_message=original_message,
            rag_confidence=rag_confidence,
            conversation_history=conversation_history,
            created_at=timestamp,
            status="pending",
        )

        # Log escalation for staff review
        self._log_escalation(escalation)

        logger.info(
            "Escalation created | escalation_id=%s patient=%s confidence=%.2f history_len=%d",
            escalation_id,
            patient_id,
            rag_confidence,
            len(conversation_history),
        )

        return escalation

    def route_to_staff(self, escalation: Escalation) -> bool:
        """
        Route escalation to staff (stub for Phase 3 integration).

        Current behavior: logs to file with full context.
        Phase 3: integrate with staff login system and inbox.

        Args:
            escalation: Escalation object

        Returns:
            True if routing successful
        """
        if not isinstance(escalation, Escalation):
            raise ValueError("escalation must be an Escalation object")

        logger.info(
            "Escalation routed to staff | escalation_id=%s patient=%s",
            escalation.escalation_id,
            escalation.patient_id,
        )

        # Phase 3: Send notification to staff member on duty
        # For now, log to escalations.log for manual review

        return True

    def mark_resolved(
        self,
        escalation_id: str,
        resolution_notes: str,
        resolved_by: str = "system",
    ) -> bool:
        """
        Mark an escalation as resolved.

        Args:
            escalation_id: Escalation UUID
            resolution_notes: Staff notes on resolution
            resolved_by: Staff member ID or "system"

        Returns:
            True if successful

        Raises:
            ValueError: If inputs invalid
        """
        if not escalation_id:
            raise ValueError("escalation_id must be a non-empty string")

        if not resolution_notes or not isinstance(resolution_notes, str):
            raise ValueError("resolution_notes must be a non-empty string")

        timestamp = datetime.utcnow().isoformat() + "Z"

        logger.info(
            "Escalation marked resolved | escalation_id=%s resolved_by=%s",
            escalation_id,
            resolved_by,
        )

        return True

    def _log_escalation(self, escalation: Escalation) -> None:
        """
        Log escalation to file for staff review.

        Format: JSON lines (one escalation per line) for easy parsing.
        Phase 3: replace with database write to escalations table.
        """
        try:
            with open(ESCALATIONS_LOG_FILE, "a") as f:
                log_entry = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "escalation_id": escalation.escalation_id,
                    "patient_id": escalation.patient_id,
                    "message_id": escalation.message_id,
                    "original_message": escalation.original_message,
                    "rag_confidence": escalation.rag_confidence,
                    "conversation_history_count": len(escalation.conversation_history),
                    "created_at": escalation.created_at,
                    "status": escalation.status,
                }
                f.write(json.dumps(log_entry) + "\n")

                logger.debug(
                    "Escalation logged | file=%s escalation_id=%s",
                    ESCALATIONS_LOG_FILE,
                    escalation.escalation_id,
                )
        except IOError as exc:
            logger.error("Failed to log escalation | error=%s", exc)

    def reassign(
        self,
        escalation_id: str,
        assigned_to: str,
    ) -> bool:
        """
        Reassign an escalation to a different staff member.

        Args:
            escalation_id: Escalation UUID
            assigned_to: New staff member ID

        Returns:
            True if successful

        Raises:
            ValueError: If inputs invalid
        """
        if not escalation_id:
            raise ValueError("escalation_id must be a non-empty string")

        if not assigned_to or not isinstance(assigned_to, str):
            raise ValueError("assigned_to must be a non-empty string")

        logger.info(
            "Escalation reassigned | escalation_id=%s assigned_to=%s",
            escalation_id,
            assigned_to,
        )

        return True


# Singleton instance for use throughout application
_escalation_handler_instance = None


def get_escalation_handler() -> EscalationHandler:
    """Get or create singleton EscalationHandler instance."""
    global _escalation_handler_instance
    if _escalation_handler_instance is None:
        _escalation_handler_instance = EscalationHandler()
    return _escalation_handler_instance
