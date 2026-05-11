"""
Patient Service — Task 2.2

Implements patient conflict resolution with:
- Upsert operations (INSERT or UPDATE based on phone+email)
- Conflict resolution (merge strategy per D-05)
- Audit trail logging for all UPDATEs
- Transaction handling (atomic operations)
- Idempotency support (phone+email uniqueness)
- Thread-safe database access

Implements D-04 (direct insert) and D-05 (conflict resolution + audit trail).
"""

import logging
import sqlite3
import threading
import json
from datetime import datetime, timedelta, date
from typing import Dict, Optional, List, Any

logger = logging.getLogger(__name__)


class PatientServiceError(Exception):
    """Base exception for PatientService errors."""
    pass


class ValidationError(PatientServiceError):
    """Raised when patient data validation fails."""
    pass


class PatientService:
    """
    Service for managing patient records with conflict resolution.

    Uses thread-safe database access with RLock for concurrent operations.
    Implements upsert pattern for idempotent patient creation.
    """

    def __init__(self, db_path: str = "clinic.db"):
        """
        Initialize PatientService.

        Args:
            db_path: Path to clinic.db (":memory:" for testing)
        """
        self.db_path = db_path
        self._lock = threading.RLock()
        self._conn = None

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create database connection with row factory."""
        with self._lock:
            if self._conn is None:
                self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
                self._conn.row_factory = sqlite3.Row
                self._conn.execute("PRAGMA journal_mode = WAL")
                self._conn.execute("PRAGMA foreign_keys = ON")
            return self._conn

    def close(self) -> None:
        """Close database connection."""
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    def _validate_patient_data(self, patient_data: dict, for_insert: bool = False) -> None:
        """
        Validate required fields in patient data.

        Args:
            patient_data: Patient record dictionary
            for_insert: If True, validate all NOT NULL fields. If False (for upsert merge), only validate core fields.

        Raises:
            ValidationError: If required fields missing or invalid
        """
        # Core required fields (always needed)
        core_fields = ["name", "phone", "email"]

        for field in core_fields:
            if field not in patient_data or not patient_data[field]:
                raise ValidationError(f"Missing required field: {field}")

        # Basic email validation
        if "@" not in patient_data["email"]:
            raise ValidationError(f"Invalid email format: {patient_data['email']}")

        # For new inserts, dob is required (NOT NULL in schema)
        if for_insert:
            if "dob" not in patient_data or not patient_data["dob"]:
                raise ValidationError("Missing required field for new patient: dob")

    def _dict_from_row(self, row: sqlite3.Row) -> dict:
        """Convert sqlite3.Row to dictionary."""
        if row is None:
            return None
        return dict(row)

    def _log_audit(self, action: str, patient_id: int, old_values: Optional[dict] = None,
                   new_values: Optional[dict] = None, updated_by: Optional[str] = None) -> None:
        """
        Log audit trail entry for patient operations.

        Args:
            action: Operation type ('patient_created' or 'patient_updated')
            patient_id: Patient ID
            old_values: Previous values (for updates)
            new_values: New/updated values
            updated_by: Staff member ID (optional)
        """
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action": action,
            "patient_id": patient_id,
            "old_values": old_values,
            "new_values": new_values,
            "updated_by": updated_by,
        }

        logger.info(json.dumps(audit_entry))

    def upsert_patient(self, patient_data: dict, updated_by: Optional[str] = None) -> int:
        """
        Insert new patient or update existing based on phone+email.

        Implements idempotency: if phone+email already exists, updates that record
        with new data (merge strategy). If not exists, creates new patient.

        Args:
            patient_data: Dictionary with patient info
                - name: str (required)
                - phone: str (required)
                - email: str (required)
                - dob: str (required for new patients, optional for updates)
                - medical_history: str (optional)
                - allergies: str (optional)
            updated_by: Staff member ID performing the action (optional)

        Returns:
            patient_id (int): ID of inserted or updated patient

        Raises:
            ValidationError: If required fields missing or invalid
            PatientServiceError: On database errors
        """
        # Validate core fields (name, phone, email always required)
        self._validate_patient_data(patient_data, for_insert=False)

        phone = patient_data.get("phone")
        email = patient_data.get("email")

        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                # Step 1: Check if patient exists by phone+email
                cursor.execute(
                    "SELECT * FROM patients WHERE phone = ? AND email = ?",
                    (phone, email),
                )
                existing_row = cursor.fetchone()

                if existing_row:
                    # Step 2a: PATIENT EXISTS - UPDATE with merge strategy
                    patient_id = existing_row["patient_id"]
                    old_values = self._dict_from_row(existing_row)

                    # Begin transaction
                    conn.execute("BEGIN TRANSACTION")

                    try:
                        # Build UPDATE statement for provided fields
                        update_fields = []
                        update_values = []

                        for field in ["name", "dob", "medical_history", "allergies"]:
                            if field in patient_data and patient_data[field] is not None:
                                update_fields.append(f"{field} = ?")
                                update_values.append(patient_data[field])

                        if update_fields:
                            # Add updated_at timestamp and updated_by
                            update_fields.append("updated_at = ?")
                            update_values.append(datetime.utcnow().isoformat() + "Z")

                            if updated_by:
                                update_fields.append("updated_by = ?")
                                update_values.append(updated_by)

                            update_values.append(patient_id)

                            update_query = f"UPDATE patients SET {', '.join(update_fields)} WHERE patient_id = ?"
                            cursor.execute(update_query, update_values)

                        conn.commit()

                        # Capture new values for audit
                        new_values = {k: patient_data.get(k) for k in patient_data
                                     if patient_data.get(k) is not None}

                        self._log_audit(
                            "patient_updated",
                            patient_id,
                            old_values=old_values,
                            new_values=new_values,
                            updated_by=updated_by,
                        )

                        logger.info(
                            "Patient updated | patient_id=%d phone=%s email=%s",
                            patient_id, phone, email
                        )

                        return patient_id

                    except Exception as e:
                        conn.rollback()
                        raise PatientServiceError(f"Failed to update patient: {str(e)}")

                else:
                    # Step 2b: PATIENT NOT EXISTS - INSERT new record
                    # For new inserts, dob is required
                    if not patient_data.get("dob"):
                        raise ValidationError("dob (date of birth) is required for new patient registration")

                    conn.execute("BEGIN TRANSACTION")

                    try:
                        cursor.execute(
                            """
                            INSERT INTO patients
                            (name, phone, email, dob, medical_history, allergies, created_at, created_by)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                patient_data.get("name"),
                                phone,
                                email,
                                patient_data.get("dob"),
                                patient_data.get("medical_history", ""),
                                patient_data.get("allergies", ""),
                                datetime.utcnow().isoformat() + "Z",
                                updated_by,
                            ),
                        )
                        conn.commit()

                        patient_id = cursor.lastrowid

                        self._log_audit(
                            "patient_created",
                            patient_id,
                            new_values=patient_data,
                            updated_by=updated_by,
                        )

                        logger.info(
                            "Patient created | patient_id=%d phone=%s email=%s",
                            patient_id, phone, email
                        )

                        return patient_id

                    except sqlite3.IntegrityError as e:
                        conn.rollback()
                        raise PatientServiceError(f"Duplicate phone+email constraint violation: {str(e)}")
                    except Exception as e:
                        conn.rollback()
                        raise PatientServiceError(f"Failed to create patient: {str(e)}")

        except (ValidationError, PatientServiceError):
            raise
        except Exception as e:
            raise PatientServiceError(f"Unexpected error in upsert_patient: {str(e)}")

    def get_patient_by_phone_email(self, phone: str, email: str) -> Optional[dict]:
        """
        Retrieve patient by phone and email (idempotency lookup).

        Args:
            phone: Patient phone number
            email: Patient email address

        Returns:
            Patient dict or None if not found

        Raises:
            PatientServiceError: On database errors
        """
        if not phone or not email:
            raise ValidationError("phone and email are required")

        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT * FROM patients WHERE phone = ? AND email = ?",
                    (phone, email),
                )
                row = cursor.fetchone()

                if row:
                    logger.debug(
                        "Patient found | phone=%s email=%s patient_id=%d",
                        phone, email, row["patient_id"]
                    )
                    return self._dict_from_row(row)
                else:
                    logger.debug("Patient not found | phone=%s email=%s", phone, email)
                    return None

        except Exception as e:
            raise PatientServiceError(f"Failed to get patient by phone+email: {str(e)}")

    def get_patient_by_id(self, patient_id: int) -> Optional[dict]:
        """
        Retrieve patient by ID (for dashboard retrieval).

        Args:
            patient_id: Patient ID

        Returns:
            Patient dict or None if not found

        Raises:
            PatientServiceError: On database errors
        """
        if not isinstance(patient_id, int) or patient_id <= 0:
            raise ValidationError("patient_id must be a positive integer")

        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                cursor.execute("SELECT * FROM patients WHERE patient_id = ?", (patient_id,))
                row = cursor.fetchone()

                if row:
                    logger.debug("Patient retrieved | patient_id=%d", patient_id)
                    return self._dict_from_row(row)
                else:
                    logger.debug("Patient not found | patient_id=%d", patient_id)
                    return None

        except Exception as e:
            raise PatientServiceError(f"Failed to get patient by ID: {str(e)}")

    def update_patient(self, patient_id: int, updates: dict, updated_by: Optional[str] = None) -> bool:
        """
        Update patient demographics and medical history (staff dashboard edits).

        Args:
            patient_id: Patient ID to update
            updates: Dictionary of fields to update
                - name: str (optional)
                - dob: str (optional)
                - medical_history: str (optional)
                - allergies: str (optional)
            updated_by: Staff member ID performing the update (optional)

        Returns:
            True if update successful

        Raises:
            ValidationError: If patient_id invalid or patient not found
            PatientServiceError: On database errors
        """
        if not isinstance(patient_id, int) or patient_id <= 0:
            raise ValidationError("patient_id must be a positive integer")

        if not updates:
            raise ValidationError("updates dictionary cannot be empty")

        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                # Step 1: Fetch current patient record
                cursor.execute("SELECT * FROM patients WHERE patient_id = ?", (patient_id,))
                existing_row = cursor.fetchone()

                if not existing_row:
                    raise ValidationError(f"Patient not found with ID: {patient_id}")

                old_values = self._dict_from_row(existing_row)

                # Step 2: Begin transaction
                conn.execute("BEGIN TRANSACTION")

                try:
                    # Build UPDATE statement for provided fields
                    update_fields = []
                    update_values = []

                    allowed_fields = ["name", "dob", "medical_history", "allergies"]

                    for field in allowed_fields:
                        if field in updates:
                            update_fields.append(f"{field} = ?")
                            update_values.append(updates[field])

                    if update_fields:
                        # Add updated_at and updated_by
                        update_fields.append("updated_at = ?")
                        update_values.append(datetime.utcnow().isoformat() + "Z")

                        if updated_by:
                            update_fields.append("updated_by = ?")
                            update_values.append(updated_by)

                        update_values.append(patient_id)

                        update_query = f"UPDATE patients SET {', '.join(update_fields)} WHERE patient_id = ?"
                        cursor.execute(update_query, update_values)

                    conn.commit()

                    # Log audit trail
                    new_values = {k: updates[k] for k in updates if k in allowed_fields}

                    self._log_audit(
                        "patient_updated",
                        patient_id,
                        old_values=old_values,
                        new_values=new_values,
                        updated_by=updated_by,
                    )

                    logger.info(
                        "Patient updated | patient_id=%d fields=%s updated_by=%s",
                        patient_id, list(new_values.keys()), updated_by
                    )

                    return True

                except Exception as e:
                    conn.rollback()
                    raise PatientServiceError(f"Failed to update patient: {str(e)}")

        except (ValidationError, PatientServiceError):
            raise
        except Exception as e:
            raise PatientServiceError(f"Unexpected error in update_patient: {str(e)}")

    def get_upcoming_appointments(self, patient_id: int, days: int = 30) -> Optional[List[Dict[str, Any]]]:
        """
        Get upcoming appointments for a patient within a time window.

        Args:
            patient_id: Patient ID
            days: Number of days ahead to look (default 30)

        Returns:
            List of appointment dicts ordered by date, or None on error
            Each dict contains: appointment_id, date, type, status

        Raises:
            ValidationError: If patient_id invalid
            PatientServiceError: On database errors
        """
        if not isinstance(patient_id, int) or patient_id <= 0:
            raise ValidationError("patient_id must be a positive integer")

        cutoff_date = date.today() + timedelta(days=days)

        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT appointment_id, appointment_date, status
                    FROM appointments
                    WHERE patient_id = ? AND appointment_date >= ? AND appointment_date <= ?
                    ORDER BY appointment_date ASC
                    """,
                    (patient_id, date.today().isoformat(), cutoff_date.isoformat())
                )

                rows = cursor.fetchall()
                appointments = [
                    {
                        'appointment_id': row[0],
                        'date': row[1],
                        'type': 'General',  # Default type; extend schema if needed
                        'status': row[2] or 'pending'
                    }
                    for row in rows
                ]

                logger.debug(
                    "Appointments retrieved | patient_id=%d count=%d days=%d",
                    patient_id,
                    len(appointments),
                    days
                )

                return appointments

        except ValueError as e:
            raise ValidationError(f"Invalid date format: {str(e)}")
        except Exception as e:
            raise PatientServiceError(f"Failed to get appointments: {str(e)}")
