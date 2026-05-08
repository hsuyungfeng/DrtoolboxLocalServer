"""HIS API Routes - Read-only clinic database queries."""

import logging
from flask import Blueprint, request, jsonify
from src.db.his_connection import get_his_connection, HISConnectionError, HISQueryTimeoutError
from src.db.query_queue import get_query_queue, QueryTask
from src.db.query_cache import QueryCache

logger = logging.getLogger(__name__)
bp = Blueprint("clinic_his", __name__, url_prefix="/api/v1/clinic-his")
cache = QueryCache()


@bp.route("/health", methods=["GET"])
def health():
    """HIS connection health check."""
    try:
        his = get_his_connection()
        queue = get_query_queue()
        return jsonify({
            "status": "healthy",
            "queue_depth": queue.queue_depth(),
            "timestamp": __import__("datetime").datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 503


@bp.route("/patient/<patient_id>", methods=["GET"])
def get_patient(patient_id):
    """Get patient demographics from HIS."""
    try:
        query = "SELECT * FROM patients WHERE patient_id = ?"
        cached = cache.get(query, (patient_id,))
        if cached:
            return jsonify(cached[0] if cached else {})

        his = get_his_connection()
        result = his.execute(query, (patient_id,))
        if result:
            cache.set(query, (patient_id,), result)
            return jsonify(result[0])
        return jsonify({})
    except Exception as e:
        logger.error(f"Patient query failed: {e}")
        return jsonify({"error": str(e)}), 503


@bp.route("/appointments", methods=["GET"])
def get_appointments():
    """Get upcoming appointments for patient."""
    patient_id = request.args.get("patient_id")
    days = request.args.get("days", "7", type=int)

    if not patient_id:
        return jsonify({"error": "patient_id required"}), 400

    try:
        query = """
            SELECT * FROM appointments 
            WHERE patient_id = ? AND appointment_date >= date('now') 
            LIMIT ?
        """
        cached = cache.get(query, (patient_id, days))
        if cached:
            return jsonify({"appointments": cached})

        his = get_his_connection()
        result = his.execute(query, (patient_id, days))
        cache.set(query, (patient_id, days), result)
        return jsonify({"appointments": result})
    except Exception as e:
        logger.error(f"Appointments query failed: {e}")
        return jsonify({"error": str(e)}), 503


@bp.route("/medications", methods=["GET"])
def get_medications():
    """Get current medications for patient."""
    patient_id = request.args.get("patient_id")

    if not patient_id:
        return jsonify({"error": "patient_id required"}), 400

    try:
        query = "SELECT * FROM medications WHERE patient_id = ? AND is_active = 1"
        cached = cache.get(query, (patient_id,))
        if cached:
            return jsonify({"medications": cached})

        his = get_his_connection()
        result = his.execute(query, (patient_id,))
        cache.set(query, (patient_id,), result)
        return jsonify({"medications": result})
    except Exception as e:
        logger.error(f"Medications query failed: {e}")
        return jsonify({"error": str(e)}), 503
