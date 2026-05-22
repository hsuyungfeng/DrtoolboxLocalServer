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

@dashboard_bp.route('/drafts', methods=['GET'])
def get_hermes_drafts():
    """Fetches nightly Hermes correction drafts."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    draft_file = os.path.join(LOG_DIR, f"hermes_drafts_{date_str}.jsonl")
    drafts = []
    if os.path.exists(draft_file):
        with open(draft_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    drafts.append(json.loads(line))
    return jsonify(drafts)

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
import time

ocr_logs = []

@dashboard_bp.route('/ocr_logs', methods=['GET'])
def get_ocr_logs():
    after = int(request.args.get('after', 0))
    return jsonify({
        "logs": ocr_logs[after:],
        "next_index": len(ocr_logs)
    })

def add_ocr_log(msg):
    timestamp = time.strftime("%H:%M:%S")
    ocr_logs.append(f"[{timestamp}] {msg}")
    # Keep only the last 200 logs to prevent memory leak
    if len(ocr_logs) > 200:
        ocr_logs.pop(0)

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
        filename = os.path.basename(filepath)
        add_ocr_log(f"開始處理檔案: {filename}")
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
                add_ocr_log(f"✅ 處理完成並加入知識庫: {filename}")
                
                # 自動刪除原始佔用空間的檔案以節省硬碟容量
                try:
                    os.remove(filepath)
                    add_ocr_log(f"🧹 自動瘦身: 已刪除原始檔 {filename}")
                except Exception as del_e:
                    add_ocr_log(f"⚠️ 自動瘦身失敗 {filename}: {str(del_e)}")
            else:
                add_ocr_log(f"⚠️ 無法萃取文字或內容為空: {filename}")
        except Exception as e:
            err_msg = f"❌ 背景處理失敗 {filename}: {str(e)}"
            logger.error(err_msg)
            add_ocr_log(err_msg)
    
    from werkzeug.utils import secure_filename
    
    for file in files:
        if file:
            original_filename = file.filename
            if not original_filename:
                continue
                
            safe_filename = secure_filename(original_filename)
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
