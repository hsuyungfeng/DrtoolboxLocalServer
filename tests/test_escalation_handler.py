"""
Test Escalation Handler Service — Task 11

Validates escalation creation, routing, resolution, and audit logging.
"""

import os
import sys
import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

# ── Path setup ─────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from services.escalation_handler import EscalationHandler, Escalation


@pytest.fixture
def handler():
    """Create EscalationHandler instance."""
    return EscalationHandler()


@pytest.fixture
def temp_log_dir(monkeypatch):
    """Create temporary directory for escalation logs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("ESCALATIONS_LOG_DIR", tmpdir)
        # Reimport to pick up new env var
        import importlib
        import services.escalation_handler as eh
        importlib.reload(eh)
        yield tmpdir


@pytest.fixture
def sample_conversation_history():
    """Sample conversation history for testing."""
    return [
        {
            "message_id": "msg_001",
            "sender": "patient",
            "text": "I have chest pain",
            "timestamp": "2026-05-08T10:00:00Z",
            "rag_confidence": None,
        },
        {
            "message_id": "msg_002",
            "sender": "bot",
            "text": "Please describe your symptoms in detail.",
            "timestamp": "2026-05-08T10:00:05Z",
            "rag_confidence": 0.75,
        },
        {
            "message_id": "msg_003",
            "sender": "patient",
            "text": "Sharp pain in the left side",
            "timestamp": "2026-05-08T10:00:30Z",
            "rag_confidence": None,
        },
    ]


class TestEscalationClass:
    """Test Escalation data class."""

    def test_escalation_creation(self):
        """Verify Escalation can be created."""
        esc = Escalation(
            escalation_id="esc_001",
            patient_id="patient_123",
            message_id="msg_001",
            original_message="Help!",
            rag_confidence=0.45,
            conversation_history=[],
            created_at="2026-05-08T10:00:00Z",
        )

        assert esc.escalation_id == "esc_001"
        assert esc.patient_id == "patient_123"
        assert esc.status == "pending"

    def test_escalation_to_dict(self):
        """Verify Escalation.to_dict() works."""
        esc = Escalation(
            escalation_id="esc_001",
            patient_id="patient_123",
            message_id="msg_001",
            original_message="Help!",
            rag_confidence=0.45,
            conversation_history=[{"text": "context"}],
            created_at="2026-05-08T10:00:00Z",
            status="resolved",
            resolution_notes="Advised to call emergency",
            resolved_by="staff_001",
            resolved_at="2026-05-08T10:05:00Z",
        )

        d = esc.to_dict()
        assert d["escalation_id"] == "esc_001"
        assert d["status"] == "resolved"
        assert d["resolution_notes"] == "Advised to call emergency"


class TestCreateEscalation:
    """Test create_escalation() method."""

    def test_create_escalation_success(self, handler, sample_conversation_history):
        """Verify escalation can be created."""
        esc = handler.create_escalation(
            patient_id="patient_123",
            original_message="What should I do?",
            rag_confidence=0.45,
            conversation_history=sample_conversation_history,
        )

        assert esc is not None
        assert esc.escalation_id is not None
        assert esc.patient_id == "patient_123"
        assert esc.original_message == "What should I do?"
        assert esc.rag_confidence == 0.45
        assert esc.status == "pending"
        assert len(esc.conversation_history) == 3

    def test_create_escalation_with_message_id(self, handler, sample_conversation_history):
        """Verify escalation with explicit message_id."""
        esc = handler.create_escalation(
            patient_id="patient_123",
            original_message="Emergency!",
            rag_confidence=0.30,
            conversation_history=sample_conversation_history,
            message_id="msg_specific",
        )

        assert esc.message_id == "msg_specific"

    def test_create_escalation_invalid_patient_id(self, handler, sample_conversation_history):
        """Verify invalid patient_id raises ValueError."""
        with pytest.raises(ValueError):
            handler.create_escalation(
                patient_id="",
                original_message="Help",
                rag_confidence=0.45,
                conversation_history=sample_conversation_history,
            )

        with pytest.raises(ValueError):
            handler.create_escalation(
                patient_id=None,
                original_message="Help",
                rag_confidence=0.45,
                conversation_history=sample_conversation_history,
            )

    def test_create_escalation_invalid_message(self, handler, sample_conversation_history):
        """Verify invalid original_message raises ValueError."""
        with pytest.raises(ValueError):
            handler.create_escalation(
                patient_id="patient_123",
                original_message="",
                rag_confidence=0.45,
                conversation_history=sample_conversation_history,
            )

        with pytest.raises(ValueError):
            handler.create_escalation(
                patient_id="patient_123",
                original_message=None,
                rag_confidence=0.45,
                conversation_history=sample_conversation_history,
            )

    def test_create_escalation_invalid_confidence(self, handler, sample_conversation_history):
        """Verify invalid rag_confidence raises ValueError."""
        with pytest.raises(ValueError):
            handler.create_escalation(
                patient_id="patient_123",
                original_message="Help",
                rag_confidence=1.5,  # > 1.0
                conversation_history=sample_conversation_history,
            )

        with pytest.raises(ValueError):
            handler.create_escalation(
                patient_id="patient_123",
                original_message="Help",
                rag_confidence=-0.1,  # < 0.0
                conversation_history=sample_conversation_history,
            )

    def test_create_escalation_invalid_history(self, handler):
        """Verify invalid conversation_history raises ValueError."""
        with pytest.raises(ValueError):
            handler.create_escalation(
                patient_id="patient_123",
                original_message="Help",
                rag_confidence=0.45,
                conversation_history="not_a_list",  # should be list
            )

    def test_create_escalation_empty_history(self, handler):
        """Verify escalation with empty history is allowed."""
        esc = handler.create_escalation(
            patient_id="patient_123",
            original_message="First message",
            rag_confidence=0.40,
            conversation_history=[],
        )

        assert esc is not None
        assert len(esc.conversation_history) == 0

    def test_create_escalation_generates_unique_ids(self, handler, sample_conversation_history):
        """Verify each escalation gets unique ID."""
        esc1 = handler.create_escalation(
            patient_id="patient_123",
            original_message="Help 1",
            rag_confidence=0.45,
            conversation_history=sample_conversation_history,
        )

        esc2 = handler.create_escalation(
            patient_id="patient_123",
            original_message="Help 2",
            rag_confidence=0.45,
            conversation_history=sample_conversation_history,
        )

        assert esc1.escalation_id != esc2.escalation_id

    def test_create_escalation_sets_timestamp(self, handler, sample_conversation_history):
        """Verify escalation has creation timestamp."""
        esc = handler.create_escalation(
            patient_id="patient_123",
            original_message="Help",
            rag_confidence=0.45,
            conversation_history=sample_conversation_history,
        )

        assert esc.created_at is not None
        # Verify ISO format with Z suffix
        assert esc.created_at.endswith("Z")


class TestRouteToStaff:
    """Test route_to_staff() method."""

    def test_route_to_staff_success(self, handler, sample_conversation_history):
        """Verify escalation can be routed to staff."""
        esc = handler.create_escalation(
            patient_id="patient_123",
            original_message="Help",
            rag_confidence=0.45,
            conversation_history=sample_conversation_history,
        )

        result = handler.route_to_staff(esc)
        assert result is True

    def test_route_to_staff_invalid_escalation(self, handler):
        """Verify invalid escalation raises ValueError."""
        with pytest.raises(ValueError):
            handler.route_to_staff("not_an_escalation")

        with pytest.raises(ValueError):
            handler.route_to_staff(None)


class TestMarkResolved:
    """Test mark_resolved() method."""

    def test_mark_resolved_success(self, handler):
        """Verify escalation can be marked resolved."""
        result = handler.mark_resolved(
            escalation_id="esc_001",
            resolution_notes="Advised to call hospital",
            resolved_by="staff_001",
        )

        assert result is True

    def test_mark_resolved_invalid_escalation_id(self, handler):
        """Verify invalid escalation_id raises ValueError."""
        with pytest.raises(ValueError):
            handler.mark_resolved(
                escalation_id="",
                resolution_notes="Some notes",
            )

        with pytest.raises(ValueError):
            handler.mark_resolved(
                escalation_id=None,
                resolution_notes="Some notes",
            )

    def test_mark_resolved_invalid_notes(self, handler):
        """Verify invalid resolution_notes raises ValueError."""
        with pytest.raises(ValueError):
            handler.mark_resolved(
                escalation_id="esc_001",
                resolution_notes="",
            )

        with pytest.raises(ValueError):
            handler.mark_resolved(
                escalation_id="esc_001",
                resolution_notes=None,
            )


class TestReassign:
    """Test reassign() method."""

    def test_reassign_success(self, handler):
        """Verify escalation can be reassigned."""
        result = handler.reassign(
            escalation_id="esc_001",
            assigned_to="staff_002",
        )

        assert result is True

    def test_reassign_invalid_escalation_id(self, handler):
        """Verify invalid escalation_id raises ValueError."""
        with pytest.raises(ValueError):
            handler.reassign(
                escalation_id="",
                assigned_to="staff_002",
            )

    def test_reassign_invalid_assigned_to(self, handler):
        """Verify invalid assigned_to raises ValueError."""
        with pytest.raises(ValueError):
            handler.reassign(
                escalation_id="esc_001",
                assigned_to="",
            )

        with pytest.raises(ValueError):
            handler.reassign(
                escalation_id="esc_001",
                assigned_to=None,
            )


class TestEscalationLogging:
    """Test escalation logging to file."""

    def test_escalation_logged_to_file(self, handler, sample_conversation_history, temp_log_dir):
        """Verify escalation is logged to file."""
        # This test requires reimport with new env var
        from services.escalation_handler import ESCALATIONS_LOG_FILE

        esc = handler.create_escalation(
            patient_id="patient_123",
            original_message="Help",
            rag_confidence=0.45,
            conversation_history=sample_conversation_history,
        )

        # Check that log file exists and contains the escalation
        assert os.path.exists(ESCALATIONS_LOG_FILE)

        with open(ESCALATIONS_LOG_FILE) as f:
            lines = f.readlines()
            assert len(lines) > 0

            # Last entry should be our escalation
            last_entry = json.loads(lines[-1])
            assert last_entry["escalation_id"] == esc.escalation_id
            assert last_entry["patient_id"] == "patient_123"
            assert last_entry["rag_confidence"] == 0.45


class TestIntegrationWithConversationManager:
    """Test integration scenarios with conversation history."""

    def test_escalation_with_low_confidence(self, handler, sample_conversation_history):
        """Verify escalation created when confidence < 60%."""
        esc = handler.create_escalation(
            patient_id="patient_123",
            original_message="Unusual symptom",
            rag_confidence=0.45,  # < 60%
            conversation_history=sample_conversation_history,
        )

        assert esc is not None
        assert esc.rag_confidence == 0.45
        assert esc.status == "pending"

    def test_escalation_at_threshold(self, handler, sample_conversation_history):
        """Verify escalation at exact 60% threshold (edge case)."""
        esc = handler.create_escalation(
            patient_id="patient_123",
            original_message="Boundary case",
            rag_confidence=0.60,  # exactly 60%
            conversation_history=sample_conversation_history,
        )

        assert esc is not None
        assert esc.rag_confidence == 0.60

    def test_escalation_includes_full_context(self, handler, sample_conversation_history):
        """Verify escalation includes complete conversation history."""
        esc = handler.create_escalation(
            patient_id="patient_123",
            original_message="Help",
            rag_confidence=0.45,
            conversation_history=sample_conversation_history,
        )

        assert len(esc.conversation_history) == 3
        assert esc.conversation_history[0]["text"] == "I have chest pain"
        assert esc.conversation_history[1]["text"] == "Please describe your symptoms in detail."


class TestSingleton:
    """Test singleton pattern for EscalationHandler."""

    def test_get_escalation_handler_singleton(self):
        """Verify get_escalation_handler returns singleton."""
        from services.escalation_handler import get_escalation_handler

        handler1 = get_escalation_handler()
        handler2 = get_escalation_handler()

        assert handler1 is handler2
