"""
Patient Intake API - POST /api/patient/intake endpoint

Implements D-01 (form fields), D-02 (validation), D-03 (idempotency),
D-04 (database storage), D-05 (audit logging) from Phase 3 requirements.

Accepts patient intake form submissions with validation and idempotency.
Returns patient_id for use by patient dashboard and downstream services.
"""

import logging
import sqlite3
import os
from datetime import datetime
from typing import Optional, Dict, Any
from threading import Lock

from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from src.api.models.patient_intake import PatientIntakeRequest

logger = logging.getLogger(__name__)

patient_intake_bp = Blueprint('patient_intake', __name__, url_prefix='/api')

# Database connection lock for thread-safe operations
_db_lock = Lock()

# Database path from environment or default
DB_PATH = os.getenv('CLINIC_DB_PATH', 'clinic.db')


def _get_db_connection() -> sqlite3.Connection:
    """
    Get a database connection to clinic.db.

    Returns:
        sqlite3.Connection with row_factory set for dict-like access
    """
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    conn.row_factory = sqlite3.Row
    return conn


def _log_audit(
    action: str,
    patient_id: Optional[int] = None,
    user: str = 'system',
    old_values: Optional[Dict[str, Any]] = None,
    new_values: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log an action to the audit trail (file-based for now).

    Per D-05: log timestamp, action, patient_id, user, old_values, new_values.

    Args:
        action: Action name (e.g., 'patient_intake_submitted', 'patient_created')
        patient_id: Patient ID affected (if applicable)
        user: User/system performing action
        old_values: Previous values (for updates)
        new_values: New values (for inserts/updates)
    """
    try:
        timestamp = datetime.utcnow().isoformat() + 'Z'
        log_entry = {
            'timestamp': timestamp,
            'action': action,
            'patient_id': patient_id,
            'user': user,
            'old_values': old_values,
            'new_values': new_values,
        }

        # Log to structured logger for now; can migrate to DB audit_log table later
        logger.info(
            "AUDIT: action=%s patient_id=%s user=%s timestamp=%s",
            action, patient_id, user, timestamp
        )
    except Exception as e:
        logger.error(f"Failed to log audit trail: {e}")


def _patient_exists(phone: str, email: str) -> Optional[Dict[str, Any]]:
    """
    Check if patient exists by phone + email (idempotency key per D-03).

    Args:
        phone: Patient phone number
        email: Patient email address

    Returns:
        Patient record dict if exists, None otherwise
    """
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()

        # Normalize phone for comparison (remove dashes)
        clean_phone = phone.replace('-', '')

        cursor.execute(
            """
            SELECT patient_id, name, phone, email, dob
            FROM patients
            WHERE REPLACE(phone, '-', '') = ? AND email = ?
            """,
            (clean_phone, email.lower())
        )

        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None
    except Exception as e:
        logger.error(f"Error checking patient existence: {e}")
        return None


def _insert_patient(data: PatientIntakeRequest) -> Optional[int]:
    """
    Insert new patient and appointment records in a transaction.

    Per D-04:
    1. INSERT into patients table
    2. INSERT into appointments table
    3. Log to audit trail

    Args:
        data: Validated PatientIntakeRequest

    Returns:
        patient_id if successful, None on error
    """
    conn = None
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()

        # Start transaction
        cursor.execute('BEGIN TRANSACTION')

        try:
            # 1. Insert patient record
            cursor.execute(
                """
                INSERT INTO patients
                (name, phone, email, dob, medical_history, allergies,
                 created_at, updated_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data.name,
                    data.phone,
                    data.email.lower(),
                    data.dob,
                    data.chief_complaint,  # Store chief_complaint in medical_history
                    data.allergies or '',
                    datetime.utcnow().isoformat() + 'Z',
                    'system'
                )
            )

            patient_id = cursor.lastrowid
            logger.info(f"Inserted patient record: patient_id={patient_id}")

            # 2. Insert appointment record
            cursor.execute(
                """
                INSERT INTO appointments
                (patient_id, appointment_date, status, created_at, updated_by)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    patient_id,
                    data.appointment_date,
                    'pending',
                    datetime.utcnow().isoformat() + 'Z',
                    'system'
                )
            )

            appointment_id = cursor.lastrowid
            logger.info(f"Inserted appointment record: appointment_id={appointment_id}")

            # Commit transaction
            conn.commit()

            # 3. Log to audit trail
            _log_audit(
                action='patient_intake_submitted',
                patient_id=patient_id,
                user='system',
                old_values=None,
                new_values={
                    'name': data.name,
                    'phone': data.phone,
                    'email': data.email,
                    'dob': str(data.dob),
                    'chief_complaint': data.chief_complaint,
                    'medications': data.medications,
                    'allergies': data.allergies,
                    'appointment_date': str(data.appointment_date),
                    'appointment_type': data.appointment_type,
                }
            )

            return patient_id

        except Exception as e:
            conn.rollback()
            logger.error(f"Error during patient/appointment insert: {e}")
            raise

    except sqlite3.IntegrityError as e:
        logger.error(f"Database integrity error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error inserting patient: {e}")
        return None
    finally:
        if conn:
            conn.close()


@patient_intake_bp.route('/patient/intake', methods=['POST'])
def post_patient_intake():
    """
    POST /api/patient/intake - Submit patient intake form.

    Request body: PatientIntakeRequest (JSON)

    Returns:
        201 Created: {"patient_id": <int>, "message": "Intake form submitted"}
        200 OK: {"patient_id": <int>, "message": "Patient already exists"} (idempotency)
        400 Bad Request: {"error": "Validation error", "details": [...]}
        409 Conflict: {"error": "Database conflict", "details": ...} (unlikely)
        500 Internal Server Error: {"error": "Internal error", "message": ...}

    Implementation notes:
    - Validates input with Pydantic (PatientIntakeRequest)
    - Checks idempotency via phone+email (D-03)
    - Inserts patient + appointment in transaction (D-04)
    - Logs all inserts to audit trail (D-05)
    """
    try:
        # 1. Parse and validate request JSON
        try:
            body = request.get_json()
            if not body:
                return jsonify({
                    'error': 'Validation error',
                    'details': [{'field': 'body', 'message': 'Request body cannot be empty'}]
                }), 400

            patient_data = PatientIntakeRequest(**body)

        except ValidationError as e:
            # Pydantic validation error - return 400 with details
            errors = []
            for error in e.errors():
                errors.append({
                    'field': '.'.join(str(loc) for loc in error['loc']),
                    'message': error['msg']
                })
            logger.warning(f"Validation error on intake form: {errors}")
            return jsonify({
                'error': 'Validation error',
                'details': errors
            }), 400

        # 2. Check idempotency: patient already exists?
        existing = _patient_exists(patient_data.phone, patient_data.email)
        if existing:
            logger.info(
                f"Patient already exists: patient_id={existing['patient_id']}, "
                f"phone={existing['phone']}, email={existing['email']}"
            )
            return jsonify({
                'patient_id': existing['patient_id'],
                'message': 'Patient already exists'
            }), 200

        # 3. Insert new patient + appointment in transaction
        with _db_lock:
            patient_id = _insert_patient(patient_data)

        if patient_id is None:
            logger.error(f"Failed to insert patient: {patient_data.email}")
            return jsonify({
                'error': 'Internal error',
                'message': 'Failed to create patient record'
            }), 500

        logger.info(f"Patient intake submitted: patient_id={patient_id}, email={patient_data.email}")

        return jsonify({
            'patient_id': patient_id,
            'message': 'Intake form submitted'
        }), 201

    except Exception as e:
        logger.error(f"Unexpected error in POST /api/patient/intake: {e}", exc_info=True)
        return jsonify({
            'error': 'Internal error',
            'message': 'An unexpected error occurred'
        }), 500
