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

import concurrent.futures
# 建立一個最多 2 名工人的背景處理池，避免瞬間爆發太多執行緒把系統卡死
ocr_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

@dashboard_bp.route('/upload', methods=['POST'])
def upload_files():
    import logging
    logger = logging.getLogger(__name__)
    
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    files = request.files.getlist('file')
    if not files or files[0].filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    data_type = request.form.get('data_type', 'special')
    from config.settings import SPECIAL_DATA_DIR, GENERAL_DATA_DIR
    target_dir = SPECIAL_DATA_DIR if data_type == 'special' else GENERAL_DATA_DIR
    
    os.makedirs(target_dir, exist_ok=True)
    saved_files = []
    
    from src.data_loader import extract_text_from_file
    from src.api.routes.chat import router
    
    # 定義一個背景執行的 OCR 工作
    def process_file_in_background(filepath, dt):
        try:
            extracted_text = extract_text_from_file(filepath)
            if extracted_text and extracted_text.strip():
                txt_path = filepath + ".txt"
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write(extracted_text)
                    
                # 辨識完成後，即時塞入 RAG 記憶體
                if router:
                    doc = {"id": txt_path, "content": extracted_text}
                    if dt == 'special':
                        router.rag.ingest_special_data([doc])
                    else:
                        router.rag.ingest_general_data([doc])
        except Exception as e:
            logger.error(f"Background OCR failed for {filepath}: {e}")
    
    for file in files:
        if file:
            original_filename = file.filename
            if not original_filename:
                continue
                
            safe_filename = os.path.basename(original_filename).replace("..", "").replace("/", "").replace("\\", "")
            if not safe_filename:
                import uuid
                safe_filename = str(uuid.uuid4())
                
            filepath = os.path.join(target_dir, safe_filename)
            file.save(filepath)
            saved_files.append(safe_filename)
            
            # 將耗時的 OCR 辨識丟給背景工人去排隊處理
            ocr_executor.submit(process_file_in_background, filepath, data_type)
            
    # 只要檔案儲存好，立刻回傳成功給網頁，避免前端等太久導致 Timeout (ERR_FAILED)
    return jsonify({"status": "success", "files": saved_files})
