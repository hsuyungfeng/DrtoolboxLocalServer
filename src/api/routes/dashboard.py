from flask import Blueprint, jsonify, request, send_file
from src.services.logger_service import logger_service
import os
from config.settings import LOG_DIR

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/logs', methods=['GET'])
def get_logs():
    logs = logger_service.get_recent_logs(limit=50)
    return jsonify(logs)

@dashboard_bp.route('/logs/correct', methods=['POST'])
def save_correction():
    data = request.json
    if not data or 'original_log' not in data or 'corrected_response' not in data:
        return jsonify({"error": "Missing required fields"}), 400
        
    success = logger_service.save_correction(data['original_log'], data['corrected_response'])
    if success:
        return jsonify({"status": "success"})
    return jsonify({"error": "Failed to save correction"}), 500

@dashboard_bp.route('/export', methods=['GET'])
def export_training_data():
    correction_file = os.path.join(LOG_DIR, "verified_training_data.jsonl")
    if not os.path.exists(correction_file):
        return jsonify({"error": "No training data available yet."}), 404
        
    return send_file(correction_file, as_attachment=True, download_name="verified_training_data.jsonl")
