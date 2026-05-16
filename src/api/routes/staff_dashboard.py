"""
Staff Dashboard Routes — Task 3.2

Implements staff CRUD operations for patient management:
- GET /dashboard/staff/patients — List patients (searchable, paginated)
- GET /dashboard/staff/patient/<patient_id> — View single patient detail
- POST /dashboard/staff/patient/<patient_id> — Update patient record

Implements D-08 (staff CRUD), D-12 (escalation indicators), D-09 (performance).
"""

import logging
import sqlite3
from functools import wraps
from datetime import datetime

from flask import Blueprint, request, render_template, jsonify

logger = logging.getLogger(__name__)

staff_dashboard_bp = Blueprint('staff_dashboard', __name__)


def require_staff_id(f):
    """Decorator to check X-Staff-ID header."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        staff_id = request.headers.get('X-Staff-ID')
        if not staff_id:
            return jsonify({'error': 'X-Staff-ID header required'}), 401
        return f(*args, staff_id=staff_id, **kwargs)
    return decorated_function


def check_escalation_status(patient_id: int, db_path: str = 'data/db/clinic.db') -> bool:
    """
    Check if patient has recent escalated messages (within 7 days).

    Args:
        patient_id: Patient ID to check
        db_path: Database path

    Returns:
        True if patient has escalation flags, False otherwise
    """
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM patient_conversations
                WHERE patient_id=? AND escalated_flag=1
                AND timestamp >= datetime('now', '-7 days')
            ''', (patient_id,))
            count = cursor.fetchone()[0]
            return count > 0
    except Exception as e:
        logger.warning(f"Error checking escalation status for patient {patient_id}: {e}")
        return False


@staff_dashboard_bp.route('/dashboard/staff/patients', methods=['GET'])
@require_staff_id
def list_patients(staff_id):
    """
    List all patients with search and pagination.

    Query params:
        - search: Name prefix or phone number (partial or full)
        - page: Page number (default: 1)

    Returns:
        Rendered HTML template with patient list
    """
    search_query = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page

    db_path = 'data/db/clinic.db'
    patients = []
    total_count = 0

    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if search_query:
                # Search by name prefix OR phone (full or partial)
                search_pattern = f'{search_query}%'
                phone_pattern = f'%{search_query}'

                cursor.execute('''
                    SELECT COUNT(*) FROM patients
                    WHERE name LIKE ? OR phone LIKE ?
                ''', (search_pattern, phone_pattern))
                total_count = cursor.fetchone()[0]

                cursor.execute('''
                    SELECT patient_id, name, phone, email, dob, created_at
                    FROM patients
                    WHERE name LIKE ? OR phone LIKE ?
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                ''', (search_pattern, phone_pattern, per_page, offset))
            else:
                # List all patients
                cursor.execute('SELECT COUNT(*) FROM patients')
                total_count = cursor.fetchone()[0]

                cursor.execute('''
                    SELECT patient_id, name, phone, email, dob, created_at
                    FROM patients
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                ''', (per_page, offset))

            rows = cursor.fetchall()
            patients = [dict(row) for row in rows]

    except Exception as e:
        logger.error(f"Error listing patients: {e}")
        return jsonify({'error': str(e)}), 500

    # Check escalation status for each patient
    for patient in patients:
        patient['has_escalation'] = check_escalation_status(patient['patient_id'], db_path)

    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1

    return render_template('staff_dashboard.html',
                         patients=patients,
                         search_query=search_query,
                         page=page,
                         total_pages=total_pages,
                         total_count=total_count)


@staff_dashboard_bp.route('/dashboard/staff/patient/<int:patient_id>', methods=['GET'])
@require_staff_id
def view_patient_detail(patient_id, staff_id):
    """
    View patient detail with edit form.

    Args:
        patient_id: ID of patient to view
        staff_id: Staff member ID (from header)

    Returns:
        Rendered patient detail template
    """
    db_path = 'data/db/clinic.db'

    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get patient record
            cursor.execute('''
                SELECT patient_id, name, phone, email, dob, medical_history, allergies, created_at
                FROM patients
                WHERE patient_id = ?
            ''', (patient_id,))
            patient_row = cursor.fetchone()

            if not patient_row:
                return render_template('staff_patient_detail.html', error='Patient not found'), 404

            patient = dict(patient_row)

            # Get upcoming appointments (next 365 days)
            cursor.execute('''
                SELECT appointment_id, appointment_date, appointment_type, status
                FROM appointments
                WHERE patient_id = ? AND appointment_date >= date('now')
                ORDER BY appointment_date ASC
                LIMIT 10
            ''', (patient_id,))
            appointments = [dict(row) for row in cursor.fetchall()]

    except Exception as e:
        logger.error(f"Error retrieving patient {patient_id}: {e}")
        return jsonify({'error': str(e)}), 500

    # Check escalation status
    has_escalation = check_escalation_status(patient_id, db_path)

    return render_template('staff_patient_detail.html',
                         patient=patient,
                         appointments=appointments,
                         has_escalation=has_escalation)


@staff_dashboard_bp.route('/dashboard/staff/patient/<int:patient_id>', methods=['POST'])
@require_staff_id
def update_patient_detail(patient_id, staff_id):
    """
    Update patient record (demographics, medical history, allergies).

    Args:
        patient_id: ID of patient to update
        staff_id: Staff member ID (from header)

    Form fields:
        - name: Patient name
        - phone: Phone number
        - email: Email address
        - dob: Date of birth (YYYY-MM-DD)
        - medical_history: Medical history text
        - allergies: Allergies text

    Returns:
        JSON response with success/error message
    """
    db_path = 'data/db/clinic.db'

    try:
        # Parse form data
        updates = {
            'name': request.form.get('name', '').strip(),
            'phone': request.form.get('phone', '').strip(),
            'email': request.form.get('email', '').strip(),
            'dob': request.form.get('dob', '').strip(),
            'medical_history': request.form.get('medical_history', '').strip(),
            'allergies': request.form.get('allergies', '').strip(),
        }

        # Validate required fields
        if not all([updates['name'], updates['phone'], updates['email'], updates['dob']]):
            return jsonify({'error': 'Name, phone, email, and DOB are required'}), 400

        # Update patient record
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE patients
                SET name = ?, phone = ?, email = ?, dob = ?, medical_history = ?, allergies = ?, updated_at = ?
                WHERE patient_id = ?
            ''', (
                updates['name'],
                updates['phone'],
                updates['email'],
                updates['dob'],
                updates['medical_history'],
                updates['allergies'],
                datetime.utcnow().isoformat(),
                patient_id
            ))

            # Log the update to audit trail (if audit table exists)
            try:
                cursor.execute('''
                    INSERT INTO audit_log (table_name, record_id, action, changes, staff_id, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    'patients',
                    patient_id,
                    'UPDATE',
                    str(updates),
                    staff_id,
                    datetime.utcnow().isoformat()
                ))
            except sqlite3.OperationalError:
                # Audit table might not exist yet - log warning but don't fail
                logger.warning("Audit table not found, skipping audit log entry")

            conn.commit()

        logger.info(f"Patient {patient_id} updated by staff {staff_id}")
        return jsonify({'success': True, 'message': 'Patient updated successfully'}), 200

    except Exception as e:
        logger.error(f"Error updating patient {patient_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
