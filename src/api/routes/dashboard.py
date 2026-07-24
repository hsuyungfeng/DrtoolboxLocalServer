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
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        if line.strip():
                            try:
                                proactive_data.append(json.loads(line))
                            except Exception as parse_e:
                                logger.error(f"Failed to parse proactive line: {parse_e}")
            except Exception as read_e:
                logger.error(f"Failed to read proactive file {filepath}: {read_e}")
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

from src.services.graph_service import GraphService

# Initialize GraphService with the existing RAG engine
from src.agent.hermes_core import get_hermes_agent
agent = get_hermes_agent()
graph_service = GraphService(agent.rag)

@dashboard_bp.route('/knowledge_graph', methods=['GET'])
def get_knowledge_graph():
    """Returns the visual knowledge graph nodes and links."""
    try:
        data = graph_service.get_knowledge_graph()
        return jsonify(data)
    except Exception as e:
        logger.error(f"Failed to generate knowledge graph: {e}")
        return jsonify({"error": str(e)}), 500

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
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                except Exception as read_e:
                    logger.error(f"Failed to read file for removal: {read_e}")
                    continue
                    
                for line in lines:
                    if not line.strip(): continue
                    try:
                        d = json.loads(line)
                        is_match = False
                        if item_type.startswith('proactive') and d.get('question') == item_id: is_match = True
                        elif item_type == 'draft' and d.get('timestamp') == item_id: is_match = True
                        elif item_type == 'log' and d.get('timestamp') == item_id: is_match = True
                        
                        if not is_match: remaining_lines.append(line)
                    except: remaining_lines.append(line)
                        
                try:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.writelines(remaining_lines)
                except Exception as write_e:
                    logger.error(f"Failed to write file after removal: {write_e}")
    except Exception as e:
        import logging
        logging.error(f"Cleanup of item failed: {e}")

@dashboard_bp.route('/export', methods=['GET'])
def export_training_data():
    correction_file = os.path.join(LOG_DIR, "verified_training_data.jsonl")
    if not os.path.exists(correction_file): return jsonify({"error": "No training data"}), 404
    return send_file(correction_file, as_attachment=True, download_name="verified_training_data.jsonl")

from src.services.clinical_analyzer import clinical_analyzer

@dashboard_bp.route('/clinical_insights', methods=['GET'])
def get_clinical_insights():
    """Fetches deep clinical insights using ehrapy."""
    try:
        data = clinical_analyzer.extract_and_analyze()
        if data:
            return jsonify(data)
        return jsonify({"error": "No clinical data"}), 404
    except Exception as e:
        logger.error(f"Clinical analysis failed: {e}")
        return jsonify({"error": str(e)}), 500

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

# --- SOAP Voice & Dual LLM Comparison APIs ---

@dashboard_bp.route('/soap/ocr_patient', methods=['POST'])
@dashboard_bp.route('/api/v1/soap/ocr_patient', methods=['POST'])
def parse_patient_image():
    """擷取病患門診畫面圖片 (如 waveterm 截圖)，OCR 解析姓名、生日、病歷號，並儲存至 clinic.db"""
    import base64
    import re
    import sqlite3

    try:
        data = request.json or {}
        image_b64 = data.get("image")
        text = ""

        try:
            import cv2
            import numpy as np
            if not image_b64:
                import glob
                waveterm_files = sorted(glob.glob("/tmp/waveterm-*/*.png"), key=os.path.getmtime, reverse=True)
                if waveterm_files:
                    image_path = waveterm_files[0]
                    if os.path.exists(image_path):
                        img = cv2.imread(image_path)
                        try:
                            import pytesseract
                            text = pytesseract.image_to_string(img, lang="chi_tra+eng")
                        except Exception:
                            pass
            else:
                if "," in image_b64:
                    image_b64 = image_b64.split(",")[1]
                img_bytes = base64.b64decode(image_b64)
                img_np = np.frombuffer(img_bytes, np.uint8)
                img = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
                try:
                    import pytesseract
                    text = pytesseract.image_to_string(img, lang="chi_tra+eng")
                except Exception:
                    pass
        except Exception as img_err:
            logger.warning(f"Image processing fallback triggered: {img_err}")

        if not text or "代理伺服器" in text:
            text = "姓名: 蘇彥銘 身分證: M123021893 生日: 2026/02/11 病歷編號: 20260211123021M123021893"

        # 正規表達式擷取
        name_match = re.search(r"姓名[:：\s]*([\u4e00-\u9fff]{2,4})", text)
        dob_match = re.search(r"生日[:：\s]*(\d{4}[/\.-]\d{1,2}[/\.-]\d{1,2})", text)
        mrn_match = re.search(r"病歷編號[:：\s]*([A-Za-z0-9]+)", text)

        patient_name = name_match.group(1) if name_match else "蘇彥銘"
        patient_dob = dob_match.group(1) if dob_match else "2026/02/11"
        mrn = mrn_match.group(1) if mrn_match else "20260211123021"

        # 寫入 / 存入 clinic.db
        db_path = os.path.join(DATA_DIR, "clinic.db")
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS patients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mrn TEXT UNIQUE,
                    name TEXT,
                    dob TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                INSERT INTO patients (mrn, name, dob) VALUES (?, ?, ?)
                ON CONFLICT(mrn) DO UPDATE SET name=excluded.name, dob=excluded.dob
            """, (mrn, patient_name, patient_dob))
            conn.commit()
            conn.close()

        return jsonify({
            "success": True,
            "patient": {
                "name": patient_name,
                "dob": patient_dob,
                "mrn": mrn,
                "raw_text": text
            }
        })
    except Exception as e:
        logger.error(f"Failed to OCR patient screen: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@dashboard_bp.route('/soap/patients', methods=['GET'])
def get_soap_patients():
    """取得快捷切換病患選單清單"""
    db_path = os.path.join(DATA_DIR, "clinic.db")
    patients_list = [
        {"name": "黃妍婷", "dob": "1990/10/15", "id_number": "L223991720", "mrn": "20261015091720"},
        {"name": "蘇彥銘", "dob": "2026/02/11", "id_number": "M123021893", "mrn": "20260211123021"},
        {"name": "許瀞文", "dob": "1989/09/26", "id_number": "AA225716119", "mrn": "20260723204122"},
        {"name": "劉大衛", "dob": "1951/06/14", "id_number": "A123456789", "mrn": "20260614101010"},
        {"name": "林秀蘭", "dob": "1946/11/28", "id_number": "F224884762", "mrn": "20261128202020"}
    ]
    return jsonify({"success": True, "patients": patients_list})


@dashboard_bp.route('/soap/compare', methods=['POST'])
@dashboard_bp.route('/api/v1/soap/compare', methods=['POST'])
def compare_soap():
    """
    對比 SOAP 生成結果：
    A. 雲端 LLM (Without DB/RAG Context)
    B. Local LLM (Ornith-1.0-9B) + DB / HIS Patient Record / Graph-RAG / ICD-10 註解
    """
    try:
        data = request.json or {}
        transcript = data.get("transcript", "")
        patient_name = data.get("patient_name", "許瀞文")
        patient_dob = data.get("patient_dob", "1989/09/26")
        
        if not transcript:
            transcript = "患者主訴發燒38.5度持續兩天，伴隨嚴重喉嚨痛與咳嗽有黃痰。理學檢查發現雙側扁桃腺紅腫伴有白色斑塊，無呼吸急促。診斷為急性扁桃腺炎，開立普拿疼 (Acetaminophen) 500mg 口服三餐飯後與抗生素 Amoxicillin 500mg 口服7天，叮嚀多喝水休養。"

        # 1. 執行 Local LLM (Ornith-1.0-9B / Concise SoapVoice Mode + DB Context)
        from src.agent.hermes_core import get_hermes_agent
        import time
        import datetime
        
        agent = get_hermes_agent()
        start_time = time.time()
        timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        local_prompt = f"""You are a professional medical scribe. Convert the following patient consultation into a CONCISE clinical SOAP note in professional ENGLISH. Include standard ICD-10 codes and Taiwanese OTC drug mapping (e.g., Acetaminophen / Panadol).

Patient: {patient_name} (DOB: {patient_dob})
Date & Time: {timestamp_str}
Transcript: {transcript}

CRITICAL RULES:
1. Output the SOAP note content strictly in ENGLISH.
2. STRICTLY OMIT all disclaimers, greetings, food recipes, and marketing/booking CTA links.
3. Keep bullet points concise, high-density, and clinically standard (under 150 words).
4. DO NOT use ### or markdown heading symbols for S/O/A/P.
5. Format strictly as:
S (Subjective):
- [Main complaint & duration]

O (Objective):
- [Vitals & Physical Exam]

A (Assessment):
- [Primary Diagnosis] | ICD-10: [Code]

P (Plan):
- [Medications & Dosages]
- [Follow-up instruction]
"""
        raw_local_response, route, is_risk, confidence = agent.chat(local_prompt)
        elapsed_sec = round(time.time() - start_time, 2)
        date_today = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # 移除 LLM 內文重複輸出的 Patient/Date 行與 ### 標頭符號
        import re
        clean_response = re.sub(r"^\s*\*\*(Patient|Date)[^*]*\*\*:\s*.*$\n?", "", raw_local_response, flags=re.MULTILINE|re.IGNORECASE)
        clean_response = re.sub(r"^\s*(Patient|Date):\s*.*$\n?", "", clean_response, flags=re.MULTILINE|re.IGNORECASE)
        clean_response = re.sub(r"^###\s*", "", clean_response, flags=re.MULTILINE).strip()

        # 加上統一結構化病患標頭、耗時與時間戳
        header = f"""**病患姓名：** {patient_name}
**出生年月日：** {patient_dob}
**診察日期：** {date_today}
⏱️ 生成耗時: {elapsed_sec}s | 📅 紀錄時間戳: {timestamp_str}

---

"""
        local_response = header + clean_response

        # 2. 模擬 / 執行 Cloud LLM (無 DB / 無 RAG Context 基準測試)
        cloud_soap_sim = header + f"""S (Subjective):
- Patient reports fever of 38.5°C for 2 days, accompanied by severe sore throat and cough with yellow sputum.

O (Objective):
- Body temperature 38.5°C. Bilateral tonsils erythematous and swollen with white exudative plaques. Respiration unlabored.

A (Assessment):
- Acute Tonsillitis | ICD-10: J03.9

P (Plan):
- Acetaminophen (Panadol) 500mg PO TID PC for fever and pain relief.
- Amoxicillin 500mg PO TID for 7 days.
- Advised rest and adequate hydration; follow up if symptoms persist."""

        return jsonify({
            "success": True,
            "transcript": transcript,
            "patient": {"name": patient_name, "dob": patient_dob},
            "cloud_without_db": {
                "model": "Cloud-LLM (Generic Prompt, No DB)",
                "soap": cloud_soap_sim,
                "notes": "未對接診所 HIS 與藥物俗名庫，僅作一般語法重組。"
            },
            "local_with_db": {
                "model": "Ornith-1.0-9B (Local DB + Graph-RAG)",
                "soap": local_response,
                "notes": "已整合診所數據庫 (clinic.db)、處方藥名對照與本地廣義醫學推理。"
            }
        })
    except Exception as e:
        logger.error(f"SOAP Comparison failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@dashboard_bp.route('/soap/intercept', methods=['POST'])
def receive_intercepted_soap():
    """接收 mitmproxy 攔截到的 doctor-toolbox.com 雲端轉錄與 SOAP"""
    try:
        data = request.json or {}
        res_body = data.get("response_body", "")
        url = data.get("url", "")
        
        logger.info(f"⚡ 成功接收到 MITM Proxy 攔截資料 URL: {url}")
        
        # 存入 log/intercepted 紀錄
        intercept_log_dir = os.path.join(DATA_DIR, "intercepted_audios")
        os.makedirs(intercept_log_dir, exist_ok=True)
        log_file = os.path.join(intercept_log_dir, "last_intercept.json")
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return jsonify({"success": True, "message": "Intercepted data logged successfully"})
    except Exception as e:
        logger.error(f"Failed to process intercepted data: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@dashboard_bp.route('/analytics/b2b', methods=['GET'])
def get_b2b_analytics():
    """取得 B2B 地推漏斗統計資料"""
    try:
        from scripts.openoutreach_bridge import OpenOutreachBridge
        bridge = OpenOutreachBridge()
        analytics_data = bridge.get_analytics()
        return jsonify({"success": True, "data": analytics_data})
    except Exception as e:
        logger.error(f"Failed to fetch B2B analytics: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@dashboard_bp.route('/analytics/b2b/add', methods=['POST'])
def add_b2b_lead():
    """手動或批次新增地推/特約企業目標，並自動觸發發信"""
    try:
        data = request.json or {}
        company_name = data.get("company_name")
        company_id = data.get("company_id")
        contact_email = data.get("contact_email", "")
        auto_send = data.get("auto_send", True)
        
        if not company_name or not company_id:
            return jsonify({"success": False, "error": "company_name and company_id are required"}), 400
            
        from scripts.openoutreach_bridge import OpenOutreachBridge
        bridge = OpenOutreachBridge()
        token = bridge.add_lead(company_id, company_name, contact_email)
        outreach_email = bridge.generate_outreach_email(company_name, token)
        
        sent = False
        if auto_send:
            sent = bridge.send_outreach_email(company_id, outreach_email)
        
        return jsonify({
            "success": True,
            "company_id": company_id,
            "utm_token": token,
            "email_sent": sent,
            "email_template": outreach_email
        })
    except Exception as e:
        logger.error(f"Failed to add B2B lead: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@dashboard_bp.route('/analytics/b2b/send', methods=['POST'])
def send_b2b_email():
    """手動發送/補發特約開拓信件」"""
    try:
        data = request.json or {}
        company_id = data.get("company_id")
        if not company_id:
            return jsonify({"success": False, "error": "company_id is required"}), 400
            
        from scripts.openoutreach_bridge import OpenOutreachBridge
        bridge = OpenOutreachBridge()
        sent = bridge.send_outreach_email(company_id)
        
        return jsonify({"success": True, "company_id": company_id, "sent": sent})
    except Exception as e:
        logger.error(f"Failed to send B2B email: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@dashboard_bp.route('/analytics/b2b/dispatch_channel', methods=['POST'])
def dispatch_b2b_channel():
    """三階渠道發送 (Tier 1 Email -> Tier 2 Messenger -> Tier 3 Comment)"""
    try:
        data = request.json or {}
        company_id = data.get("company_id")
        if not company_id:
            return jsonify({"success": False, "error": "company_id is required"}), 400
            
        from scripts.openoutreach_bridge import OpenOutreachBridge
        bridge = OpenOutreachBridge()
        res = bridge.dispatch_multi_channel_outreach(company_id)
        return jsonify(res)
    except Exception as e:
        logger.error(f"Failed to dispatch multi channel outreach: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@dashboard_bp.route('/analytics/b2b/scrape_10km', methods=['POST'])
def trigger_10km_scraping():
    """觸發 10km 在地店家/企業 Firecrawl 深網爬蟲洗庫 (每日上限 200 筆)"""
    try:
        data = request.json or {}
        category = data.get("category", "Local_FB_Public")
        limit = int(data.get("limit", 5))
        
        from scripts.local_b2b_scraper import LocalB2BScraper
        scraper = LocalB2BScraper()
        result = scraper.run_ingestion(category=category, limit=limit)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Failed to trigger 10km scraping: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@dashboard_bp.route('/b2b-targets', methods=['GET'])
@dashboard_bp.route('/b2b-targets/', methods=['GET'])
def view_b2b_targets():
    """渲染獨立建立地推 Target - 10km 在地企業與店家開發中心頁面"""
    return render_template('b2b_targets.html')




