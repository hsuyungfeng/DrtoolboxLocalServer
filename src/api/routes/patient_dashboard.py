"""
Patient Dashboard API - Task 3.1

Implements patient read-only dashboard with:
- GET /dashboard/patient/<patient_id> endpoint
- Patient record display (name, contact, medical summary)
- Upcoming appointments listing
- Conversation history (last 7 days)
- 5-minute cache TTL for patient data
- <1s page load time performance target
- Strictly read-only interface (D-07, D-09)
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from flask import Blueprint, render_template, request
from src.services.patient_service import PatientService
from src.services.conversation_manager import ConversationManager

logger = logging.getLogger(__name__)

patient_dashboard_bp = Blueprint('patient_dashboard', __name__)

# Cache configuration
CACHE_TTL = 300  # 5 minutes
_patient_cache: Dict[int, Any] = {}
_cache_timestamps: Dict[int, float] = {}


def get_cached_patient(patient_id: int) -> Optional[Dict[str, Any]]:
    """
    Get patient from cache (5min TTL) or return None if expired.

    Args:
        patient_id: Patient ID to look up

    Returns:
        Patient dict if cached and not expired, None otherwise
    """
    now = time.time()
    if patient_id in _patient_cache:
        cache_age = now - _cache_timestamps.get(patient_id, 0)
        if cache_age < CACHE_TTL:
            logger.debug(f"Cache hit for patient {patient_id} (age: {cache_age:.2f}s)")
            return _patient_cache[patient_id]
        else:
            # Cache expired, remove it
            del _patient_cache[patient_id]
            del _cache_timestamps[patient_id]
            logger.debug(f"Cache expired for patient {patient_id} (age: {cache_age:.2f}s)")

    return None


def set_patient_cache(patient_id: int, patient_data: Dict[str, Any]) -> None:
    """
    Store patient in cache with timestamp.

    Args:
        patient_id: Patient ID
        patient_data: Patient record dictionary
    """
    _patient_cache[patient_id] = patient_data
    _cache_timestamps[patient_id] = time.time()
    logger.debug(f"Cached patient {patient_id}")


@patient_dashboard_bp.route('/dashboard/patient/<int:patient_id>', methods=['GET'])
def view_patient_dashboard(patient_id: int):
    """
    Render patient dashboard (read-only view).

    Fetches patient record, upcoming appointments, and conversation history.
    Returns 404 if patient not found.

    Args:
        patient_id: Patient ID from URL

    Returns:
        Rendered HTML template with patient data, or 404 error
    """
    try:
        # Try cache first
        patient = get_cached_patient(patient_id)

        if not patient:
            # Fetch from PatientService
            patient_service = PatientService(db_path='clinic.db')
            patient = patient_service.get_patient_by_id(patient_id)

            if not patient:
                logger.warning(f"Patient not found: patient_id={patient_id}")
                return render_template('patient_dashboard.html',
                                     error='Patient not found'), 404

            # Cache for 5 minutes
            set_patient_cache(patient_id, patient)
        else:
            # If we got from cache, still need to service instance for appointments
            patient_service = PatientService(db_path='clinic.db')

        # Fetch upcoming appointments (next 30 days)
        appointments = patient_service.get_upcoming_appointments(patient_id, days=30)
        if appointments is None:
            appointments = []

        # Fetch conversation history (last 7 days)
        conv_manager = ConversationManager(db_path='clinic.db')
        conversation_messages = conv_manager.get_conversation_history(patient_id, days=7)

        # Convert Message objects to dicts for template rendering
        conversation_history = [msg.to_dict() for msg in conversation_messages]

        logger.info(f"Dashboard loaded for patient {patient_id} | "
                   f"appointments={len(appointments)} | "
                   f"messages={len(conversation_history)}")

        return render_template('patient_dashboard.html',
                             patient=patient,
                             appointments=appointments,
                             conversation_history=conversation_history,
                             last_updated=datetime.utcnow().isoformat() + 'Z',
                             error=None)

    except Exception as e:
        logger.error(f"Error loading patient dashboard: {e}", exc_info=True)
        return render_template('patient_dashboard.html',
                             error='Failed to load patient dashboard'), 500
