"""
Staff API - Conversation History & Escalation Endpoints (Task 12)

Provides authenticated endpoints for staff to retrieve:
  - GET /api/patient/{patient_id}/conversations — 7-day history with privacy controls
  - GET /api/patient/{patient_id}/escalations — escalated messages for follow-up

Authentication: X-Staff-ID header (stub for Phase 3 staff login integration)
Privacy: no sensitive HIS data, only RAG responses and escalation context
Audit logging: all accesses logged with staff ID, timestamp, patient ID
"""

import logging
import os
from datetime import datetime
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

staff_bp = Blueprint("staff_api", __name__, url_prefix="/api")

# ────────────────────────────────────────────────────────────
# Authentication & Authorization
# ────────────────────────────────────────────────────────────

def _get_staff_id_from_request() -> str | None:
    """
    Extract staff ID from X-Staff-ID header.

    Phase 3: replace with JWT token validation and session lookup.

    Returns:
        staff_id if authenticated, None otherwise
    """
    staff_id = request.headers.get("X-Staff-ID", "").strip()
    return staff_id if staff_id else None


def _authenticate_staff() -> tuple[bool, str | None]:
    """
    Authenticate staff member.

    Returns:
        (authenticated: bool, staff_id: str | None)
    """
    staff_id = _get_staff_id_from_request()

    if not staff_id:
        logger.warning("Unauthenticated access attempt | path=%s", request.path)
        return False, None

    # Phase 3: validate staff_id against clinic staff database
    # For now, any non-empty staff_id is accepted

    logger.info("Staff authenticated | staff_id=%s", staff_id)
    return True, staff_id


def _audit_log_access(staff_id: str, patient_id: str, endpoint: str, success: bool = True) -> None:
    """
    Log staff access for privacy audit.

    Args:
        staff_id: Staff member ID
        patient_id: Patient being accessed
        endpoint: API endpoint accessed
        success: Whether access was successful
    """
    logger.info(
        "Staff access audit | staff_id=%s patient_id=%s endpoint=%s success=%s timestamp=%s",
        staff_id,
        patient_id,
        endpoint,
        success,
        datetime.utcnow().isoformat() + "Z",
    )


# ────────────────────────────────────────────────────────────
# Conversation History Endpoint
# ────────────────────────────────────────────────────────────

@staff_bp.route("/patient/<patient_id>/conversations", methods=["GET"])
def get_conversation_history(patient_id: str):
    """
    Retrieve conversation history for a patient with privacy controls.

    Query parameters:
      - days: Number of days to retrieve (default 7)

    Returns:
        200: [{"timestamp", "sender", "text", "rag_confidence"}, ...]
        400: Invalid query parameters
        403: Not authenticated
        404: Patient not found
        500: Database error

    SC-4 verification: history accurate & retrievable within <500ms
    """
    # ── Authentication ──
    authenticated, staff_id = _authenticate_staff()
    if not authenticated:
        return jsonify({"error": "Unauthorized"}), 403

    # ── Input validation ──
    days = request.args.get("days", "7")
    try:
        days = int(days)
        if days < 1 or days > 365:
            return jsonify({"error": "days must be between 1 and 365"}), 400
    except ValueError:
        return jsonify({"error": "days must be an integer"}), 400

    if not patient_id or len(patient_id) == 0:
        return jsonify({"error": "patient_id required"}), 400

    # ── Retrieve conversation history ──
    try:
        from services.conversation_manager import ConversationManager

        mgr = ConversationManager()
        history = mgr.get_conversation_history(patient_id, days=days)

        _audit_log_access(staff_id, patient_id, "GET /conversations", success=True)

        # Convert to JSON-serializable format
        result = [
            {
                "timestamp": msg.timestamp,
                "sender": msg.sender,
                "text": msg.text,
                "rag_confidence": msg.rag_confidence,
            }
            for msg in history
        ]

        logger.info(
            "Conversation history retrieved | staff_id=%s patient_id=%s count=%d",
            staff_id,
            patient_id,
            len(result),
        )

        return jsonify(result), 200

    except Exception as exc:
        logger.error(
            "Error retrieving conversation history | staff_id=%s patient_id=%s error=%s",
            staff_id,
            patient_id,
            exc,
            exc_info=True,
        )
        _audit_log_access(staff_id, patient_id, "GET /conversations", success=False)
        return jsonify({"error": "Internal server error"}), 500


# ────────────────────────────────────────────────────────────
# Escalations Endpoint
# ────────────────────────────────────────────────────────────

@staff_bp.route("/patient/<patient_id>/escalations", methods=["GET"])
def get_patient_escalations(patient_id: str):
    """
    Retrieve escalated messages for a patient.

    Query parameters:
      - days: Number of days to look back (default 7)

    Returns:
        200: [{"timestamp", "text", "escalated_flag", "rag_confidence"}, ...]
        400: Invalid query parameters
        403: Not authenticated
        404: Patient not found
        500: Database error
    """
    # ── Authentication ──
    authenticated, staff_id = _authenticate_staff()
    if not authenticated:
        return jsonify({"error": "Unauthorized"}), 403

    # ── Input validation ──
    days = request.args.get("days", "7")
    try:
        days = int(days)
        if days < 1 or days > 365:
            return jsonify({"error": "days must be between 1 and 365"}), 400
    except ValueError:
        return jsonify({"error": "days must be an integer"}), 400

    if not patient_id or len(patient_id) == 0:
        return jsonify({"error": "patient_id required"}), 400

    # ── Retrieve escalated messages ──
    try:
        from services.conversation_manager import ConversationManager

        mgr = ConversationManager()
        escalated = mgr.get_escalated_messages(patient_id, days=days)

        _audit_log_access(staff_id, patient_id, "GET /escalations", success=True)

        result = [
            {
                "timestamp": msg.timestamp,
                "text": msg.text,
                "escalated_flag": msg.escalated_flag,
                "rag_confidence": msg.rag_confidence,
            }
            for msg in escalated
        ]

        logger.info(
            "Escalations retrieved | staff_id=%s patient_id=%s count=%d",
            staff_id,
            patient_id,
            len(result),
        )

        return jsonify(result), 200

    except Exception as exc:
        logger.error(
            "Error retrieving escalations | staff_id=%s patient_id=%s error=%s",
            staff_id,
            patient_id,
            exc,
            exc_info=True,
        )
        _audit_log_access(staff_id, patient_id, "GET /escalations", success=False)
        return jsonify({"error": "Internal server error"}), 500


# ────────────────────────────────────────────────────────────
# Health Check
# ────────────────────────────────────────────────────────────

@staff_bp.route("/staff/health", methods=["GET"])
def staff_api_health():
    """Health check for staff API subsystem."""
    return jsonify({
        "status": "ok",
        "service": "staff_api",
        "endpoints": [
            "GET /api/patient/{patient_id}/conversations",
            "GET /api/patient/{patient_id}/escalations",
        ],
    })
