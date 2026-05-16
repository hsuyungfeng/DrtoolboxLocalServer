"""
LINE User to Patient Linking API (Task 4.1)

Provides manual linking endpoints for staff to map LINE users to patients:
  - POST /api/staff/link-line-user — Manual linking by staff (no auto-matching)
  - GET /api/staff/unlinked-line-users — List LINE users without patient mapping
  - POST /api/staff/unlink-line-user/<line_user_id> — Remove mapping (staff only)

Authentication: X-Staff-ID header (Phase 3 stub, upgraded in Phase 4)
Privacy: Idempotent linking, audit trail with staff_id and timestamp
Error handling: 409 Conflict on duplicate, 404 if not found, 400 for validation
"""

import logging
import os
import sqlite3
from datetime import datetime
from functools import wraps
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

line_linking_bp = Blueprint("line_linking", __name__, url_prefix="/api")

# ────────────────────────────────────────────────────────────
# Database connection
# ────────────────────────────────────────────────────────────

def _get_db_connection():
    """Get database connection (uses clinic.db)."""
    try:
        # Try to connect to clinic database (used by other services)
        conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), '../../../data/db/clinic.db'))
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
        return None


# ────────────────────────────────────────────────────────────
# Authentication & Authorization
# ────────────────────────────────────────────────────────────

def require_staff_id(f):
    """
    Decorator to check X-Staff-ID header is present.

    Phase 3: Simple header validation
    Phase 4: Replace with JWT token validation and clinic auth
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        staff_id = request.headers.get("X-Staff-ID", "").strip()

        if not staff_id:
            logger.warning(f"Unauthenticated access attempt | path={request.path}")
            return jsonify({"error": "X-Staff-ID header required"}), 401

        # Phase 3: any non-empty staff_id is accepted
        # Phase 4: validate against clinic staff database

        logger.info(f"Staff authenticated | staff_id={staff_id} path={request.path}")
        return f(*args, staff_id=staff_id, **kwargs)

    return decorated_function


# ────────────────────────────────────────────────────────────
# Audit Logging
# ────────────────────────────────────────────────────────────

def _audit_log_linking(action: str, line_user_id: str, patient_id: int, staff_id: str) -> None:
    """
    Log LINE user linking/unlinking operations for audit trail.

    Args:
        action: "line_user_linked" or "line_user_unlinked"
        line_user_id: LINE user ID being linked/unlinked
        patient_id: Patient ID being linked to (or None if unlinking)
        staff_id: Staff member performing the action
    """
    timestamp = datetime.utcnow().isoformat() + "Z"
    log_entry = {
        "timestamp": timestamp,
        "action": action,
        "line_user_id": line_user_id,
        "patient_id": patient_id,
        "staff_id": staff_id,
    }

    logger.info(f"LINE linking audit | {log_entry}")


# ────────────────────────────────────────────────────────────
# Helper functions
# ────────────────────────────────────────────────────────────

def _patient_exists(patient_id: int) -> bool:
    """Check if patient exists in database."""
    conn = _get_db_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM patients WHERE patient_id = ?", (patient_id,))
        result = cursor.fetchone()
        return result is not None
    except sqlite3.Error as e:
        logger.error(f"Database error checking patient: {e}")
        return False
    finally:
        conn.close()


def _get_mapping(line_user_id: str) -> dict | None:
    """Get existing mapping for a LINE user."""
    conn = _get_db_connection()
    if not conn:
        return None

    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, line_user_id, patient_id, created_at, linked_by FROM line_user_mapping WHERE line_user_id = ?",
            (line_user_id,)
        )
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "line_user_id": row[1],
                "patient_id": row[2],
                "created_at": row[3],
                "linked_by": row[4],
            }
        return None
    except sqlite3.Error as e:
        logger.error(f"Database error checking mapping: {e}")
        return None
    finally:
        conn.close()


def _create_mapping(line_user_id: str, patient_id: int, staff_id: str) -> dict | None:
    """Create a new LINE user to patient mapping."""
    conn = _get_db_connection()
    if not conn:
        return None

    try:
        cursor = conn.cursor()
        created_at = datetime.utcnow().isoformat() + "Z"

        cursor.execute(
            """INSERT INTO line_user_mapping (line_user_id, patient_id, created_at, linked_by)
               VALUES (?, ?, ?, ?)""",
            (line_user_id, patient_id, created_at, staff_id)
        )
        conn.commit()
        mapping_id = cursor.lastrowid

        logger.info(f"Mapping created | id={mapping_id} line_user_id={line_user_id} patient_id={patient_id}")
        return {
            "id": mapping_id,
            "line_user_id": line_user_id,
            "patient_id": patient_id,
            "created_at": created_at,
            "linked_by": staff_id,
        }
    except sqlite3.IntegrityError as e:
        logger.error(f"Duplicate mapping or integrity error: {e}")
        return None
    except sqlite3.Error as e:
        logger.error(f"Database error creating mapping: {e}")
        return None
    finally:
        conn.close()


def _delete_mapping(line_user_id: str) -> dict | None:
    """Delete a LINE user mapping and return the deleted mapping info."""
    conn = _get_db_connection()
    if not conn:
        return None

    try:
        cursor = conn.cursor()

        # Get mapping before deletion
        cursor.execute(
            "SELECT id, patient_id FROM line_user_mapping WHERE line_user_id = ?",
            (line_user_id,)
        )
        row = cursor.fetchone()

        if not row:
            return None

        mapping_id, patient_id = row[0], row[1]

        # Delete mapping
        cursor.execute("DELETE FROM line_user_mapping WHERE line_user_id = ?", (line_user_id,))
        conn.commit()

        logger.info(f"Mapping deleted | id={mapping_id} line_user_id={line_user_id}")
        return {
            "id": mapping_id,
            "line_user_id": line_user_id,
            "patient_id": patient_id,
        }
    except sqlite3.Error as e:
        logger.error(f"Database error deleting mapping: {e}")
        return None
    finally:
        conn.close()


def _get_unlinked_users() -> list[dict] | None:
    """Get list of LINE users without patient mappings."""
    conn = _get_db_connection()
    if not conn:
        return None

    try:
        cursor = conn.cursor()

        # Query: Find LINE users in conversation history without a mapping
        # Using message_router or LINE conversation tables from Phase 2
        cursor.execute("""
            SELECT DISTINCT
                lh.line_user_id,
                MAX(lh.timestamp) as last_message_timestamp
            FROM line_history lh
            LEFT JOIN line_user_mapping lum ON lh.line_user_id = lum.line_user_id
            WHERE lum.id IS NULL
            GROUP BY lh.line_user_id
            ORDER BY last_message_timestamp DESC
        """)

        rows = cursor.fetchall()
        unlinked_users = []

        for row in rows:
            unlinked_users.append({
                "line_user_id": row[0],
                "last_message_timestamp": row[1],
            })

        logger.info(f"Retrieved {len(unlinked_users)} unlinked LINE users")
        return unlinked_users
    except sqlite3.Error as e:
        logger.error(f"Database error retrieving unlinked users: {e}")
        # Return empty list if table doesn't exist yet
        return []
    finally:
        conn.close()


# ────────────────────────────────────────────────────────────
# Endpoints
# ────────────────────────────────────────────────────────────

@line_linking_bp.route("/staff/link-line-user", methods=["POST"])
@require_staff_id
def link_line_user(staff_id: str):
    """
    Manually link a LINE user to a patient.

    Request body:
        {
            "line_user_id": "U12345abcde",
            "patient_id": 42
        }

    Returns:
        201 Created: {"success": true, "mapping_id": 1, "message": "LINE user linked to patient"}
        400 Bad Request: Missing or invalid parameters
        404 Not Found: Patient not found
        409 Conflict: LINE user already linked to a patient
        500 Internal Error: Database error

    D-15: Manual staff linking (no auto-matching, privacy-preserving)
    D-16: Fallback lookup for unlinked users
    """
    # Validate request body
    if not request.is_json:
        return jsonify({"error": "Request body must be JSON"}), 400

    data = request.get_json()
    line_user_id = data.get("line_user_id", "").strip()
    patient_id = data.get("patient_id")

    # Validate parameters
    if not line_user_id:
        return jsonify({"error": "line_user_id is required and must not be empty"}), 400

    if patient_id is None or not isinstance(patient_id, int):
        return jsonify({"error": "patient_id is required and must be an integer"}), 400

    # Check if patient exists
    if not _patient_exists(patient_id):
        logger.warning(f"Linking attempt to non-existent patient | patient_id={patient_id} staff_id={staff_id}")
        return jsonify({"error": "Patient not found"}), 404

    # Check if mapping already exists (idempotency - prevent duplicates)
    existing_mapping = _get_mapping(line_user_id)
    if existing_mapping:
        logger.warning(f"Duplicate linking attempt | line_user_id={line_user_id} staff_id={staff_id}")
        return jsonify({
            "error": "LINE user already linked",
            "details": f"Line user {line_user_id} is already linked to patient {existing_mapping['patient_id']}"
        }), 409

    # Create mapping
    mapping = _create_mapping(line_user_id, patient_id, staff_id)
    if not mapping:
        logger.error(f"Failed to create mapping | line_user_id={line_user_id} patient_id={patient_id}")
        return jsonify({"error": "Failed to create mapping"}), 500

    # Audit log
    _audit_log_linking("line_user_linked", line_user_id, patient_id, staff_id)

    return jsonify({
        "success": True,
        "mapping_id": mapping["id"],
        "message": "LINE user linked to patient",
    }), 201


@line_linking_bp.route("/staff/unlinked-line-users", methods=["GET"])
@require_staff_id
def get_unlinked_users(staff_id: str):
    """
    List LINE users without a patient mapping.

    Returns:
        200 OK: {
            "unlinked_users": [
                {"line_user_id": "U12345abcde", "last_message_timestamp": "2026-05-10T15:30:00Z"},
                ...
            ],
            "count": 2
        }
        500 Internal Error: Database error

    D-16: Fallback lookup for unlinked users
    """
    # Audit access
    logger.info(f"Staff retrieving unlinked LINE users | staff_id={staff_id}")

    # Get unlinked users
    unlinked_users = _get_unlinked_users()
    if unlinked_users is None:
        logger.error(f"Failed to retrieve unlinked users | staff_id={staff_id}")
        return jsonify({"error": "Failed to retrieve unlinked users"}), 500

    return jsonify({
        "unlinked_users": unlinked_users,
        "count": len(unlinked_users),
    }), 200


@line_linking_bp.route("/staff/unlink-line-user/<line_user_id>", methods=["POST"])
@require_staff_id
def unlink_line_user(line_user_id: str, staff_id: str):
    """
    Remove a LINE user to patient mapping.

    Args:
        line_user_id: LINE user ID to unlink

    Returns:
        200 OK: {"success": true, "message": "Mapping removed"}
        404 Not Found: Mapping not found
        500 Internal Error: Database error

    D-15: Manual staff unlinking (for corrections or re-linking)
    """
    # Validate line_user_id
    if not line_user_id or not line_user_id.strip():
        return jsonify({"error": "line_user_id is required"}), 400

    line_user_id = line_user_id.strip()

    # Delete mapping
    deleted_mapping = _delete_mapping(line_user_id)
    if not deleted_mapping:
        logger.warning(f"Attempt to unlink non-existent mapping | line_user_id={line_user_id} staff_id={staff_id}")
        return jsonify({
            "error": "Mapping not found",
            "details": f"No mapping found for LINE user {line_user_id}"
        }), 404

    # Audit log
    _audit_log_linking("line_user_unlinked", line_user_id, deleted_mapping["patient_id"], staff_id)

    return jsonify({
        "success": True,
        "message": "Mapping removed",
    }), 200


# ────────────────────────────────────────────────────────────
# Health check
# ────────────────────────────────────────────────────────────

@line_linking_bp.route("/staff/line-linking/health", methods=["GET"])
def line_linking_health():
    """Health check for LINE linking service."""
    conn = _get_db_connection()
    if conn:
        conn.close()
        db_status = "healthy"
    else:
        db_status = "unhealthy"

    return jsonify({
        "service": "line_linking",
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
    }), 200
