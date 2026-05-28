from flask import Blueprint, jsonify, request, send_file
from werkzeug.utils import secure_filename
from src.services.logger_service import logger_service
import os
import json
import datetime
import concurrent.futures
import time
import logging
from config.settings import LOG_DIR, SPECIAL_DATA_DIR, GENERAL_DATA_DIR, PROJECT_ROOT, DATA_DIR

logger = logging.getLogger(__name__)
dashboard_bp = Blueprint('dashboard', __name__)

# --- Background Worker Pool ---
ocr_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
ocr_logs = []

def add_ocr_log(msg):
    timestamp = time.strftime("%H:%M:%S")
    ocr_logs.append(f"[{timestamp}] {msg}")
    if len(ocr_logs) > 200: ocr_logs.pop(0)

def process_file_in_background(filepath, dt):
    """Background task to handle text extraction and RAG ingestion."""
    from src.data_loader import extract_text_from_file
    from src.agent.hermes_core import get_hermes_agent
    
    filename = os.path.basename(filepath)
    add_ocr_log(f"開始處理檔案: {filename}")
    try:
        extracted_text = extract_text_from_file(filepath)
        if extracted_text and extracted_text.strip():
            txt_path = filepath + ".txt"
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(extracted_text)
                
            # 即時塞入 RAG 記憶體
            agent = get_hermes_agent()
            doc = {"id": txt_path, "content": extracted_text}
            if dt == 'special':
                agent.rag.ingest_special_data([doc])
            else:
                agent.rag.ingest_general_data([doc])
                
            add_ocr_log(f"✅ 處理完成並加入知識庫: {filename}")
            
            # 自動瘦身
            try:
                os.remove(filepath)
                add_ocr_log(f"🧹 自動瘦身: 已刪除原始檔 {filename}")
            except Exception as del_e:
                add_ocr_log(f"⚠️ 自動瘦身失敗 {filename}: {str(del_e)}")
        else:
            add_ocr_log(f"⚠️ 無法萃取文字或內容為空: {filename}")
    except Exception as e:
        import logging
        err_msg = f"❌ 背景處理失敗 {filename}: {str(e)}"
        logging.getLogger(__name__).error(err_msg)
        add_ocr_log(err_msg)

# --- Routes ---

@dashboard_bp.route('/logs', methods=['GET'])
def get_logs():
    logs = logger_service.get_recent_logs(limit=50)
    return jsonify(logs)

@dashboard_bp.route('/drafts', methods=['GET'])
def get_hermes_drafts():
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    draft_file = os.path.join(LOG_DIR, f"hermes_drafts_{date_str}.jsonl")
    drafts = []
    if os.path.exists(draft_file):
        with open(draft_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip(): drafts.append(json.loads(line))
    return jsonify(drafts)

@dashboard_bp.route('/proactive', methods=['GET'])
def get_proactive_qa():
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    proactive_data = []
    for cat in ['special', 'general', '']:
        filename = f"proactive_qa_{cat}_{date_str}.jsonl" if cat else f"proactive_qa_{date_str}.jsonl"
        filepath = os.path.join(LOG_DIR, filename)
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip(): proactive_data.append(json.loads(line))
    return jsonify(proactive_data)

@dashboard_bp.route('/articles', methods=['GET'])
def get_articles():
    article_file = os.path.join(PROJECT_ROOT, "data/evaluation/articles_to_post.json")
    if os.path.exists(article_file):
        with open(article_file, 'r', encoding='utf-8') as f: return jsonify(json.load(f))
    return jsonify([])

@dashboard_bp.route('/articles/sync', methods=['POST'])
def mark_article_synced():
    data = request.json
    title = data.get('title')
    if not title: return jsonify({"error": "Missing title"}), 400
    article_file = os.path.join(PROJECT_ROOT, "data/evaluation/articles_to_post.json")
    if os.path.exists(article_file):
        with open(article_file, 'r', encoding='utf-8') as f: articles = json.load(f)
        new_articles = [f for f in articles if f.get('title') != title]
        with open(article_file, 'w', encoding='utf-8') as f: json.dump(new_articles, f, ensure_ascii=False, indent=4)
    return jsonify({"status": "success"})

@dashboard_bp.route('/upload_base64', methods=['POST'])
def upload_base64():
    import base64
    data = request.json
    if not data or 'file_data' not in data or 'filename' not in data:
        return jsonify({"error": "Missing data"}), 400
        
    filename = secure_filename(data['filename'])
    if not filename:
        filename = data['filename'].replace("/", "").replace("\\", "").replace("..", "")
        if not filename: return jsonify({"error": "Invalid filename"}), 400

    data_type = data.get('data_type', 'special')
    target_dir = SPECIAL_DATA_DIR if data_type == 'special' else GENERAL_DATA_DIR
    
    os.makedirs(target_dir, exist_ok=True)
    filepath = os.path.join(target_dir, filename)
    
    try:
        img_data = base64.b64decode(data['file_data'])
        with open(filepath, 'wb') as f:
            f.write(img_data)
        
        ocr_executor.submit(process_file_in_background, filepath, data_type)
        return jsonify({"status": "success", "filename": filename})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@dashboard_bp.route('/upload', methods=['POST', 'OPTIONS'])
def upload_files():
    if request.method == 'OPTIONS': return jsonify({"status": "ok"})
    if 'file' not in request.files: return jsonify({"error": "No file part"}), 400
    files = request.files.getlist('file')
    if not files or files[0].filename == '': return jsonify({"error": "No selected file"}), 400
    data_type = request.form.get('data_type', 'special')
    target_dir = SPECIAL_DATA_DIR if data_type == 'special' else GENERAL_DATA_DIR
    os.makedirs(target_dir, exist_ok=True)
    
    # 嚴格的白名單與過濾邏輯
    SUPPORTED_EXTS = {'.pdf', '.jpg', '.jpeg', '.png', '.ppt', '.pptx', '.doc', '.docx', '.txt', '.md', '.mp4', '.mp3', '.m4a', '.wav', '.flv'}
    
    saved_files = []
    for file in files:
        if file and file.filename:
            orig = file.filename
            
            # 1. 排除隱藏檔與 Office 暫存檔
            if orig.startswith('.') or orig.startswith('~$'):
                continue
                
            # 2. 嚴格檢查副檔名
            ext = os.path.splitext(orig)[1].lower()
            if ext not in SUPPORTED_EXTS:
                # 特別處理：如果完全沒副檔名，也要擋掉
                logger.info(f"Skipping junk/unsupported file: {orig}")
                continue
                
            safe_filename = secure_filename(orig)
            if not safe_filename:
                safe_filename = orig.replace("/", "").replace("\\", "").replace("..", "")
            
            filepath = os.path.join(target_dir, safe_filename)
            try:
                file.save(filepath)
                saved_files.append(safe_filename)
                ocr_executor.submit(process_file_in_background, filepath, data_type)
            except Exception: continue
                
    return jsonify({"status": "success", "files": saved_files})

@dashboard_bp.route('/logs/batch_correct', methods=['POST'])
def save_batch_corrections():
    data = request.json
    if not data or 'corrections' not in data:
        return jsonify({"error": "Missing corrections list"}), 400
    
    corrections = data['corrections']
    success_count = 0
    errors = []
    
    for item in corrections:
        try:
            original_log = item['original_log']
            corrected_response = item['corrected_response']
            edited_prompt = item.get('corrected_prompt')
            
            if edited_prompt:
                original_log['messages'][0]['content'] = edited_prompt
                
            success = logger_service.save_correction(original_log, corrected_response)
            if success:
                _remove_from_source(item.get('item_type'), item.get('item_id'))
                success_count += 1
            else:
                errors.append(f"Failed to save item {item.get('item_id')}")
        except Exception as e:
            errors.append(str(e))
            
    return jsonify({
        "status": "success" if not errors else "partial_success",
        "success_count": success_count,
        "errors": errors
    })

@dashboard_bp.route('/logs/correct', methods=['POST'])
def save_correction():
    data = request.json
    if not data or 'original_log' not in data or 'corrected_response' not in data:
        return jsonify({"error": "Missing required fields"}), 400
    edited_prompt = data.get('corrected_prompt')
    original_log = data['original_log']
    if edited_prompt: original_log['messages'][0]['content'] = edited_prompt
    success = logger_service.save_correction(original_log, data['corrected_response'])
    if not success: return jsonify({"error": "Failed to save correction"}), 500
    _remove_from_source(data.get('item_type'), data.get('item_id'))
    return jsonify({"status": "success"})

@dashboard_bp.route('/logs/batch_discard', methods=['POST'])
def batch_discard_items():
    data = request.json
    if not data or 'items' not in data:
        return jsonify({"error": "Missing items list"}), 400
    
    items = data['items']
    success_count = 0
    for item in items:
        try:
            _remove_from_source(item.get('item_type'), item.get('item_id'))
            success_count += 1
        except Exception: continue
            
    return jsonify({
        "status": "success",
        "count": success_count
    })

@dashboard_bp.route('/logs/discard', methods=['POST'])
def discard_item():
    data = request.json
    if not data or 'item_type' not in data or 'item_id' not in data:
        return jsonify({"error": "Missing required fields"}), 400
    _remove_from_source(data['item_type'], data['item_id'])
    return jsonify({"status": "success"})

def _remove_from_source(item_type, item_id):
    if not item_type or not item_id: return
    try:
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        files_to_check = []
        if item_type == 'draft':
            files_to_check.append(f"hermes_drafts_{date_str}.jsonl")
        elif item_type == 'log':
            files_to_check.append(f"interactions_{date_str}.jsonl")
        else: # proactive
            files_to_check.extend([f"proactive_qa_special_{date_str}.jsonl", f"proactive_qa_general_{date_str}.jsonl", f"proactive_qa_{date_str}.jsonl"])
            
        for filename in files_to_check:
            filepath = os.path.join(LOG_DIR, filename)
            if os.path.exists(filepath):
                remaining_lines = []
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        if not line.strip(): continue
                        try:
                            d = json.loads(line)
                            is_match = False
                            if item_type.startswith('proactive') and d.get('question') == item_id: is_match = True
                            elif item_type == 'draft' and d.get('timestamp') == item_id: is_match = True
                            elif item_type == 'log' and d.get('timestamp') == item_id: is_match = True
                            
                            if not is_match: remaining_lines.append(line)
                        except: remaining_lines.append(line)
                        
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.writelines(remaining_lines)
    except Exception as e:
        import logging
        logging.error(f"Cleanup of item failed: {e}")

@dashboard_bp.route('/export', methods=['GET'])
def export_training_data():
    correction_file = os.path.join(LOG_DIR, "verified_training_data.jsonl")
    if not os.path.exists(correction_file): return jsonify({"error": "No training data"}), 404
    return send_file(correction_file, as_attachment=True, download_name="verified_training_data.jsonl")

@dashboard_bp.route('/analytics', methods=['GET'])
def get_analytics():
    """Fetches structured analytics data for the BI Dashboard."""
    path = os.path.join(DATA_DIR, "analytics_data.json")
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    return jsonify({"top_procedures": [], "pain_points": []})

@dashboard_bp.route('/ocr_logs', methods=['GET'])
def get_ocr_logs():
    after = int(request.args.get('after', 0))
    return jsonify({"logs": ocr_logs[after:], "next_index": len(ocr_logs)})

@dashboard_bp.route('/drafts/trigger', methods=['POST'])
def trigger_fact_check():
    import subprocess
    try:
        subprocess.Popen(['uv', 'run', 'python', 'scripts/nightly_fact_check.py'])
        subprocess.Popen(['uv', 'run', 'python', 'scripts/nightly_qa_generator.py'])
        subprocess.Popen(['uv', 'run', 'python', 'scripts/weekly_crm_insights.py'])
        return jsonify({"status": "started"})
    except Exception as e: return jsonify({"error": str(e)}), 500
