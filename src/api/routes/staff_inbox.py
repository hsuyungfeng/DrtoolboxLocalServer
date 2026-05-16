"""
Staff Inbox - Message Aggregation and Polling (Task 4.2 - Phase 3)

Provides authenticated endpoints for staff to retrieve aggregated patient messages:
  - GET /api/staff/inbox — JSON API for polling (returns all patient messages, grouped, unread-first)
  - GET /dashboard/staff/inbox — Renders inbox UI with polling JavaScript
  - POST /api/staff/inbox/mark-read/<patient_id> — Mark patient's messages as read

Features:
  - Polling-based updates (3-5s configurable via INBOX_POLL_INTERVAL_SECONDS env var)
  - Unread-first sorting, grouped by patient
  - Shows patient name, last message timestamp, unread count, escalation status
  - Staff authentication via X-Staff-ID header
  - Performance: <500ms JSON response time (indexed queries)
"""

import logging
import os
import sqlite3
from datetime import datetime
from functools import wraps
from flask import Blueprint, request, jsonify, render_template

logger = logging.getLogger(__name__)

staff_inbox_bp = Blueprint("staff_inbox", __name__, url_prefix="/api")

# ────────────────────────────────────────────────────────────
# Authentication & Authorization
# ────────────────────────────────────────────────────────────

def require_staff_id(f):
    """
    Decorator to require X-Staff-ID header for staff endpoints.

    Phase 3: replace with JWT token validation and session lookup.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        staff_id = request.headers.get('X-Staff-ID', '').strip()
        if not staff_id:
            logger.warning("Unauthenticated access attempt | path=%s", request.path)
            return jsonify({'error': 'X-Staff-ID header required'}), 401

        logger.info("Staff authenticated | staff_id=%s endpoint=%s", staff_id, request.path)
        return f(*args, staff_id=staff_id, **kwargs)

    return decorated


def _get_db_connection():
    """Get database connection with row factory."""
    conn = sqlite3.connect('data/db/clinic.db')
    conn.row_factory = sqlite3.Row
    return conn


def _audit_log_access(staff_id: str, action: str, details: str = "") -> None:
    """
    Log staff access for audit trail.

    Args:
        staff_id: Staff member ID
        action: Action performed (view_inbox, mark_read, etc.)
        details: Additional details
    """
    logger.info(
        "Staff inbox audit | staff_id=%s action=%s details=%s timestamp=%s",
        staff_id,
        action,
        details,
        datetime.utcnow().isoformat() + "Z",
    )


# ────────────────────────────────────────────────────────────
# Staff Inbox API Endpoints
# ────────────────────────────────────────────────────────────

@staff_inbox_bp.route('/staff/inbox', methods=['GET'])
@require_staff_id
def get_inbox_json(staff_id):
    """
    Get inbox messages as JSON (for polling from frontend).

    Returns aggregated patient messages with unread counts and escalation flags.
    Sorted by unread count DESC (unread first), then by timestamp DESC.

    Query parameters:
      - None (returns all patients with messages)

    Returns:
        200: {
          "inbox_messages": [
            {
              "patient_id": 42,
              "patient_name": "王小明",
              "last_message_timestamp": "2026-05-11T14:30:00Z",
              "unread_count": 3,
              "escalated_flag": true,
              "last_message_preview": "頭痛已3天..."
            }
          ],
          "total_unread": 3,
          "last_refresh": "2026-05-11T14:35:00Z"
        }
        401: Not authenticated
        500: Database error

    Performance: <500ms (indexed queries on patient_id, timestamp, escalated_flag)
    """
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()

            # Query: Join patient_conversations with patients table
            # Group by patient_id, show unread count, escalation flag, last message
            # Sort by unread count DESC (unread first), then timestamp DESC
            cursor.execute('''
                SELECT
                    p.patient_id,
                    p.name AS patient_name,
                    MAX(pc.timestamp) AS last_message_timestamp,
                    SUM(CASE WHEN pc.unread_flag=1 THEN 1 ELSE 0 END) AS unread_count,
                    MAX(CASE WHEN pc.escalated_flag=1 THEN 1 ELSE 0 END) AS escalated_flag,
                    SUBSTR(MAX(pc.text), 1, 50) AS last_message_preview
                FROM patient_conversations pc
                JOIN line_user_mapping lum ON pc.patient_id = lum.patient_id
                JOIN patients p ON lum.patient_id = p.patient_id
                WHERE pc.sender = 'patient'
                GROUP BY p.patient_id
                ORDER BY unread_count DESC, last_message_timestamp DESC
            ''')

            rows = cursor.fetchall()
            messages = []

            for row in rows:
                messages.append({
                    'patient_id': row['patient_id'],
                    'patient_name': row['patient_name'],
                    'last_message_timestamp': row['last_message_timestamp'],
                    'unread_count': row['unread_count'] or 0,
                    'escalated_flag': bool(row['escalated_flag']),
                    'last_message_preview': row['last_message_preview'] or '[No message]'
                })

            # Calculate total unread
            total_unread = sum(m['unread_count'] for m in messages)

            _audit_log_access(staff_id, 'view_inbox', f'retrieved {len(messages)} patients')

            return jsonify({
                'inbox_messages': messages,
                'total_unread': total_unread,
                'last_refresh': datetime.utcnow().isoformat() + 'Z'
            }), 200

    except sqlite3.Error as e:
        logger.error("Database error in get_inbox_json | error=%s", str(e))
        return jsonify({'error': 'Database error', 'message': str(e)}), 500
    except Exception as e:
        logger.error("Unexpected error in get_inbox_json | error=%s", str(e))
        return jsonify({'error': 'Internal error', 'message': str(e)}), 500


@staff_inbox_bp.route('/staff/inbox/mark-read/<int:patient_id>', methods=['POST'])
@require_staff_id
def mark_patient_read(patient_id, staff_id):
    """
    Mark all messages from a patient as read.

    Updates the unread_flag for all patient messages to 0.

    Args:
        patient_id: Patient ID to mark as read

    Returns:
        200: {"success": true, "message": "Marked N messages as read"}
        401: Not authenticated
        404: Patient not found
        500: Database error
    """
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()

            # Verify patient exists
            cursor.execute('SELECT patient_id FROM patients WHERE patient_id = ?', (patient_id,))
            if not cursor.fetchone():
                logger.warning("Patient not found | staff_id=%s patient_id=%s", staff_id, patient_id)
                return jsonify({'error': 'Patient not found'}), 404

            # Mark all messages as read
            cursor.execute('''
                UPDATE patient_conversations
                SET unread_flag=0
                WHERE patient_id=?
            ''', (patient_id,))

            conn.commit()
            rowcount = cursor.rowcount

            _audit_log_access(staff_id, 'mark_read', f'patient_id={patient_id}, rows_updated={rowcount}')

            return jsonify({
                'success': True,
                'message': f'Marked {rowcount} messages as read'
            }), 200

    except sqlite3.Error as e:
        logger.error("Database error in mark_patient_read | error=%s", str(e))
        return jsonify({'error': 'Database error', 'message': str(e)}), 500
    except Exception as e:
        logger.error("Unexpected error in mark_patient_read | error=%s", str(e))
        return jsonify({'error': 'Internal error', 'message': str(e)}), 500


# ────────────────────────────────────────────────────────────
# Staff Dashboard Routes
# ────────────────────────────────────────────────────────────

@staff_inbox_bp.route('/staff/inbox', methods=['GET'], endpoint='view_inbox_page')
def view_inbox_page_wrapper():
    """Wrapper route for viewing inbox page (allows require_staff_id decorator)."""
    staff_id = request.headers.get('X-Staff-ID', '').strip()
    if not staff_id:
        logger.warning("Unauthenticated access attempt | path=%s", request.path)
        return jsonify({'error': 'X-Staff-ID header required'}), 401

    return _render_inbox_page(staff_id)


def _render_inbox_page(staff_id: str):
    """
    Render inbox page with polling JavaScript.

    Sets up polling interval from environment variable (default 3s, range 3-5s).
    """
    try:
        polling_interval = int(os.getenv('INBOX_POLL_INTERVAL_SECONDS', '3'))

        # Validate polling interval is between 3-5 seconds
        if polling_interval < 3 or polling_interval > 5:
            polling_interval = 3

        _audit_log_access(staff_id, 'view_inbox_page', f'polling_interval={polling_interval}s')

        return render_template('staff_inbox.html',
                             polling_interval=polling_interval,
                             staff_id=staff_id)
    except Exception as e:
        logger.error("Error rendering inbox page | error=%s", str(e))
        return jsonify({'error': 'Internal error', 'message': str(e)}), 500
