from flask import Blueprint, jsonify, request, send_file
from werkzeug.utils import secure_filename
from src.services.logger_service import logger_service
import os
from config.settings import LOG_DIR, SPECIAL_DATA_DIR

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

@dashboard_bp.route('/upload', methods=['POST'])
def upload_files():
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Received upload request. Files: {request.files.keys()}, Form: {request.form.keys()}")
    
    if 'file' not in request.files:
        logger.error("No 'file' in request.files")
        return jsonify({"error": "No file part"}), 400
    
    files = request.files.getlist('file')
    if not files:
        logger.error("request.files.getlist('file') is empty")
        return jsonify({"error": "No selected file list"}), 400
        
    if files[0].filename == '':
        logger.error("First file has an empty filename")
        return jsonify({"error": "No selected file"}), 400
        
    data_type = request.form.get('data_type', 'special')
    from config.settings import SPECIAL_DATA_DIR, GENERAL_DATA_DIR
    target_dir = SPECIAL_DATA_DIR if data_type == 'special' else GENERAL_DATA_DIR
    
    os.makedirs(target_dir, exist_ok=True)
    saved_files = []
    
    from src.data_loader import extract_text_from_file
    from src.api.routes.chat import router
    
    for file in files:
        if file:
            # 避免 secure_filename 吃掉中文檔名，手動清理路徑跳脫字元
            original_filename = file.filename
            if not original_filename:
                continue
                
            safe_filename = os.path.basename(original_filename).replace("..", "").replace("/", "").replace("\\", "")
            if not safe_filename:
                import uuid
                safe_filename = str(uuid.uuid4())
                
            filepath = os.path.join(target_dir, safe_filename)
            file.save(filepath)
            
            # Extract text
            extracted_text = extract_text_from_file(filepath)
            if extracted_text and extracted_text.strip():
                txt_path = filepath + ".txt"
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write(extracted_text)
                    
                # Dynamically update the RAG engine if router is initialized
                if router:
                    doc = {"id": txt_path, "content": extracted_text}
                    if data_type == 'special':
                        router.rag.ingest_special_data([doc])
                    else:
                        router.rag.ingest_general_data([doc])
            
            saved_files.append(filename)
            
    return jsonify({"status": "success", "files": saved_files})
