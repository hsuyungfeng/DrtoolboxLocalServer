"""
Staff Actions API - 員工操作 API

提供員工對升級、預約、訊息的操作功能

Endpoints:
- GET /api/v1/escalations/list - 取得待處理升級列表
- POST /api/v1/escalations/<id>/approve - 批准升級
- POST /api/v1/escalations/<id>/reject - 拒絕升級
- POST /api/v1/escalations/<id>/assign - 指派處理人員
- GET /api/v1/appointments/list - 取得預約列表
- POST /api/v1/appointments/create - 建立新預約
- PUT /api/v1/appointments/<id> - 更新預約
- DELETE /api/v1/appointments/<id> - 取消預約
- POST /api/v1/messages/send - 發送訊息給患者
- POST /api/v1/messages/broadcast - 廣播訊息
"""

import os
import sys
import sqlite3
import logging
from datetime import datetime
from flask import Blueprint, jsonify, request

# Fix import paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

logger = logging.getLogger(__name__)

# Create Blueprint
staff_actions_bp = Blueprint('staff_actions', __name__)

# Database path
DB_PATH = os.environ.get('CLINIC_DB_PATH', os.path.join(os.path.dirname(__file__), '../../../clinic.db'))


def get_db_connection():
    """取得資料庫連線"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class DBContext:
    """Context manager for database connections - ensures proper cleanup"""
    def __enter__(self):
        self.conn = get_db_connection()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()
        return False


def require_staff_auth():
    """驗證員工身份"""
    staff_id = request.headers.get('X-Staff-ID')
    if not staff_id:
        return None, jsonify({
            'success': False,
            'error': '需要 X-Staff-ID header',
            'code': 'AUTH_REQUIRED'
        }), 401
    return staff_id, None, None


# ============================================================================
# Escalation APIs (升級處理)
# ============================================================================

@staff_actions_bp.route('/api/v1/escalations/list', methods=['GET'])
def list_escalations():
    """取得所有待處理升級列表"""
    staff_id, error, status = require_staff_auth()
    if error:
        return error, status

    try:
        with DBContext() as conn:
            cursor = conn.cursor()

            # 取得所有已升級的對話
            cursor.execute('''
                SELECT
                    pc.id,
                    pc.patient_id,
                    pc.message_id,
                    pc.text,
                    pc.timestamp,
                    pc.rag_confidence,
                    p.name as patient_name,
                    p.phone as patient_phone
                FROM patient_conversations pc
                LEFT JOIN patients p ON pc.patient_id = p.patient_id
                WHERE pc.escalated_flag = 1
                ORDER BY pc.timestamp DESC
                LIMIT 100
            ''')
            rows = cursor.fetchall()

            escalations = []
            for row in rows:
                escalations.append({
                    'id': row['id'],
                    'patient_id': row['patient_id'],
                    'patient_name': row['patient_name'] or '未知患者',
                    'patient_phone': row['patient_phone'] or '--',
                    'message': row['text'],
                    'confidence': row['rag_confidence'],
                    'created_at': row['timestamp']
                })

        return jsonify({
            'success': True,
            'data': {
                'escalations': escalations,
                'total': len(escalations)
            }
        })

    except Exception as e:
        logger.error(f"Error listing escalations: {e}")
        return jsonify({
            'success': False,
            'error': '無法取得升級列表',
            'message': str(e)
        }), 500


@staff_actions_bp.route('/api/v1/escalations/<int:escalation_id>/approve', methods=['POST'])
def approve_escalation(escalation_id):
    """批准升級"""
    staff_id, error, status = require_staff_auth()
    if error:
        return error, status

    try:
        data = request.get_json() or {}
        notes = data.get('notes', '')

        with DBContext() as conn:
            cursor = conn.cursor()

            # 更新為已處理
            cursor.execute('''
                UPDATE patient_conversations
                SET escalated_flag = 0
                WHERE id = ?
            ''', (escalation_id,))

            conn.commit()

        logger.info(f"Escalation {escalation_id} approved by staff {staff_id}")

        return jsonify({
            'success': True,
            'message': '升級已批准',
            'data': {
                'escalation_id': escalation_id,
                'approved_by': staff_id,
                'approved_at': datetime.utcnow().isoformat()
            }
        })

    except Exception as e:
        logger.error(f"Error approving escalation: {e}")
        return jsonify({
            'success': False,
            'error': '無法批准升級',
            'message': str(e)
        }), 500


@staff_actions_bp.route('/api/v1/escalations/<int:escalation_id>/reject', methods=['POST'])
def reject_escalation(escalation_id):
    """拒絕升級"""
    staff_id, error, status = require_staff_auth()
    if error:
        return error, status

    try:
        data = request.get_json() or {}
        notes = data.get('notes', '')

        with DBContext() as conn:
            cursor = conn.cursor()

            # 標記為已處理（不解釋原因）
            cursor.execute('''
                UPDATE patient_conversations
                SET escalated_flag = 0
                WHERE id = ?
            ''', (escalation_id,))

            conn.commit()

        logger.info(f"Escalation {escalation_id} rejected by staff {staff_id}")

        return jsonify({
            'success': True,
            'message': '升級已拒絕',
            'data': {
                'escalation_id': escalation_id,
                'rejected_by': staff_id,
                'rejected_at': datetime.utcnow().isoformat()
            }
        })

    except Exception as e:
        logger.error(f"Error rejecting escalation: {e}")
        return jsonify({
            'success': False,
            'error': '無法拒絕升級',
            'message': str(e)
        }), 500


@staff_actions_bp.route('/api/v1/escalations/<int:escalation_id>/assign', methods=['POST'])
def assign_escalation(escalation_id):
    """指派處理人員"""
    staff_id, error, status = require_staff_auth()
    if error:
        return error, status

    try:
        data = request.get_json() or {}
        assigned_to = data.get('assigned_to')

        if not assigned_to:
            return jsonify({
                'success': False,
                'error': '需要指定指派人員'
            }), 400

        logger.info(f"Escalation {escalation_id} assigned to {assigned_to} by {staff_id}")

        return jsonify({
            'success': True,
            'message': f'已指派給 {assigned_to}',
            'data': {
                'escalation_id': escalation_id,
                'assigned_to': assigned_to,
                'assigned_by': staff_id,
                'assigned_at': datetime.utcnow().isoformat()
            }
        })

    except Exception as e:
        logger.error(f"Error assigning escalation: {e}")
        return jsonify({
            'success': False,
            'error': '無法指派升級',
            'message': str(e)
        }), 500


# ============================================================================
# Appointment APIs (預約管理)
# ============================================================================

@staff_actions_bp.route('/api/v1/appointments/list', methods=['GET'])
def list_appointments():
    """取得預約列表"""
    staff_id, error, status = require_staff_auth()
    if error:
        return error, status

    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        status_filter = request.args.get('status')

        with DBContext() as conn:
            cursor = conn.cursor()

            query = '''
                SELECT
                    a.appointment_id,
                    a.patient_id,
                    a.appointment_date,
                    a.status,
                    a.created_at,
                    p.name as patient_name,
                    p.phone as patient_phone
                FROM appointments a
                LEFT JOIN patients p ON a.patient_id = p.patient_id
                WHERE 1=1
            '''
            params = []

            if start_date:
                query += ' AND date(a.appointment_date) >= ?'
                params.append(start_date)

            if end_date:
                query += ' AND date(a.appointment_date) <= ?'
                params.append(end_date)

            if status_filter:
                query += ' AND a.status = ?'
                params.append(status_filter)

            query += ' ORDER BY a.appointment_date ASC LIMIT 100'

            cursor.execute(query, params)
            rows = cursor.fetchall()

            appointments = []
            for row in rows:
                appointments.append({
                    'appointment_id': row['appointment_id'],
                    'patient_id': row['patient_id'],
                    'patient_name': row['patient_name'] or '未知患者',
                    'patient_phone': row['patient_phone'] or '--',
                    'appointment_date': row['appointment_date'],
                    'status': row['status'],
                    'created_at': row['created_at']
                })

        return jsonify({
            'success': True,
            'data': {
                'appointments': appointments,
                'total': len(appointments)
            }
        })

    except Exception as e:
        logger.error(f"Error listing appointments: {e}")
        return jsonify({
            'success': False,
            'error': '無法取得預約列表',
            'message': str(e)
        }), 500


@staff_actions_bp.route('/api/v1/appointments/create', methods=['POST'])
def create_appointment():
    """建立新預約"""
    staff_id, error, status = require_staff_auth()
    if error:
        return error, status

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'error': '需要提供預約資料'
            }), 400

        patient_id = data.get('patient_id')
        appointment_date = data.get('appointment_date')
        notes = data.get('notes', '').strip()

        # Validate patient_id
        if not patient_id:
            return jsonify({
                'success': False,
                'error': '患者 ID 必須提供'
            }), 400

        if not isinstance(patient_id, int) or patient_id <= 0:
            return jsonify({
                'success': False,
                'error': '患者 ID 必須是正整數'
            }), 400

        # Validate appointment_date format and value
        if not appointment_date:
            return jsonify({
                'success': False,
                'error': '預約日期必須提供'
            }), 400

        try:
            appt_date = datetime.strptime(appointment_date, '%Y-%m-%d')
            if appt_date.date() <= datetime.now().date():
                return jsonify({
                    'success': False,
                    'error': '預約日期必須為未來日期'
                }), 400
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'error': '預約日期格式無效，請使用 YYYY-MM-DD'
            }), 400

        with DBContext() as conn:
            cursor = conn.cursor()

            # Verify patient exists
            cursor.execute('SELECT patient_id FROM patients WHERE patient_id = ?', (patient_id,))
            if not cursor.fetchone():
                return jsonify({
                    'success': False,
                    'error': f'患者 {patient_id} 不存在'
                }), 404

            cursor.execute('''
                INSERT INTO appointments (patient_id, appointment_date, status, created_by, updated_by)
                VALUES (?, ?, 'pending', ?, ?)
            ''', (patient_id, appointment_date, staff_id, staff_id))

            appointment_id = cursor.lastrowid
            conn.commit()

        logger.info(f"Appointment {appointment_id} created by staff {staff_id}")

        return jsonify({
            'success': True,
            'message': '預約已建立',
            'data': {
                'appointment_id': appointment_id,
                'patient_id': patient_id,
                'appointment_date': appointment_date,
                'status': 'pending',
                'created_by': staff_id
            }
        }), 201

    except Exception as e:
        logger.error(f"Error creating appointment: {e}")
        return jsonify({
            'success': False,
            'error': '無法建立預約',
            'message': str(e)
        }), 500


@staff_actions_bp.route('/api/v1/appointments/<int:appointment_id>', methods=['PUT'])
def update_appointment(appointment_id):
    """更新預約"""
    staff_id, error, status = require_staff_auth()
    if error:
        return error, status

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'error': '需要提供更新資料'
            }), 400

        # Whitelist allowed fields to prevent injection
        ALLOWED_FIELDS = {'appointment_date', 'status'}
        update_fields = {k: v for k, v in data.items() if k in ALLOWED_FIELDS}

        if not update_fields:
            return jsonify({
                'success': False,
                'error': '沒有有效的欄位要更新'
            }), 400

        # Validate status if provided
        if 'status' in update_fields:
            valid_statuses = {'pending', 'confirmed', 'completed', 'cancelled'}
            if update_fields['status'] not in valid_statuses:
                return jsonify({
                    'success': False,
                    'error': f'無效的狀態。允許：{", ".join(valid_statuses)}'
                }), 400

        # Validate appointment_date if provided
        if 'appointment_date' in update_fields:
            try:
                appt_date = datetime.strptime(update_fields['appointment_date'], '%Y-%m-%d')
                if appt_date.date() <= datetime.now().date():
                    return jsonify({
                        'success': False,
                        'error': '預約日期必須為未來日期'
                    }), 400
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'error': '預約日期格式無效，請使用 YYYY-MM-DD'
                }), 400

        with DBContext() as conn:
            cursor = conn.cursor()

            # Build parameterized query safely
            set_clauses = [f'{key} = ?' for key in update_fields.keys()]
            set_clauses.append('updated_by = ?')
            set_clauses.append('updated_at = CURRENT_TIMESTAMP')

            params = list(update_fields.values()) + [staff_id, appointment_id]

            query = f'UPDATE appointments SET {", ".join(set_clauses)} WHERE appointment_id = ?'
            cursor.execute(query, params)
            conn.commit()

        logger.info(f"Appointment {appointment_id} updated by staff {staff_id}")

        return jsonify({
            'success': True,
            'message': '預約已更新',
            'data': {
                'appointment_id': appointment_id,
                'updated_by': staff_id,
                'updated_at': datetime.utcnow().isoformat()
            }
        })

    except Exception as e:
        logger.error(f"Error updating appointment: {e}")
        return jsonify({
            'success': False,
            'error': '無法更新預約',
            'message': str(e)
        }), 500


@staff_actions_bp.route('/api/v1/appointments/<int:appointment_id>', methods=['DELETE'])
def cancel_appointment(appointment_id):
    """取消預約"""
    staff_id, error, status = require_staff_auth()
    if error:
        return error, status

    try:
        with DBContext() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE appointments
                SET status = 'cancelled', updated_by = ?, updated_at = CURRENT_TIMESTAMP
                WHERE appointment_id = ?
            ''', (staff_id, appointment_id))

            conn.commit()

        logger.info(f"Appointment {appointment_id} cancelled by staff {staff_id}")

        return jsonify({
            'success': True,
            'message': '預約已取消',
            'data': {
                'appointment_id': appointment_id,
                'status': 'cancelled',
                'cancelled_by': staff_id
            }
        })

    except Exception as e:
        logger.error(f"Error cancelling appointment: {e}")
        return jsonify({
            'success': False,
            'error': '無法取消預約',
            'message': str(e)
        }), 500


# ============================================================================
# Message APIs (訊息發送)
# ============================================================================

@staff_actions_bp.route('/api/v1/messages/send', methods=['POST'])
def send_message():
    """發送訊息給患者"""
    staff_id, error, status = require_staff_auth()
    if error:
        return error, status

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'error': '需要提供訊息資料'
            }), 400

        patient_id = data.get('patient_id')
        message_text = data.get('text', '').strip()
        channel = data.get('channel', 'web')
        require_reply = data.get('require_reply', False)

        if not patient_id or not message_text:
            return jsonify({
                'success': False,
                'error': '需要患者 ID 和訊息內容'
            }), 400

        if not isinstance(patient_id, int) or patient_id <= 0:
            return jsonify({
                'success': False,
                'error': '患者 ID 必須是正整數'
            }), 400

        if len(message_text) > 1000:
            return jsonify({
                'success': False,
                'error': '訊息內容不能超過 1000 字'
            }), 400

        # 儲存訊息到對話歷史
        with DBContext() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO patient_conversations
                (patient_id, sender, text, rag_confidence, escalated_flag)
                VALUES (?, 'staff', ?, NULL, 0)
            ''', (patient_id, message_text))

            message_id = cursor.lastrowid
            conn.commit()

        logger.info(f"Message {message_id} sent to patient {patient_id} by staff {staff_id}")

        return jsonify({
            'success': True,
            'message': '訊息已發送',
            'data': {
                'message_id': message_id,
                'patient_id': patient_id,
                'sent_by': staff_id,
                'sent_at': datetime.utcnow().isoformat()
            }
        }), 201

    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return jsonify({
            'success': False,
            'error': '無法發送訊息',
            'message': str(e)
        }), 500


@staff_actions_bp.route('/api/v1/messages/broadcast', methods=['POST'])
def broadcast_message():
    """廣播訊息給所有患者"""
    staff_id, error, status = require_staff_auth()
    if error:
        return error, status

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'error': '需要提供廣播內容'
            }), 400

        message_text = data.get('text', '').strip()
        channel = data.get('channel', 'web')

        if not message_text:
            return jsonify({
                'success': False,
                'error': '需要廣播內容'
            }), 400

        if len(message_text) > 1000:
            return jsonify({
                'success': False,
                'error': '廣播內容不能超過 1000 字'
            }), 400

        with DBContext() as conn:
            cursor = conn.cursor()

            # 取得所有患者
            cursor.execute('SELECT patient_id FROM patients')
            patients = cursor.fetchall()

            broadcast_count = 0
            for patient in patients:
                cursor.execute('''
                    INSERT INTO patient_conversations
                    (patient_id, sender, text, rag_confidence, escalated_flag)
                    VALUES (?, 'staff', ?, NULL, 0)
                ''', (patient['patient_id'], message_text))
                broadcast_count += 1

            conn.commit()

        logger.info(f"Broadcast sent to {broadcast_count} patients by staff {staff_id}")

        return jsonify({
            'success': True,
            'message': f'廣播已發送給 {broadcast_count} 位患者',
            'data': {
                'broadcast_count': broadcast_count,
                'sent_by': staff_id,
                'sent_at': datetime.utcnow().isoformat()
            }
        }), 201

    except Exception as e:
        logger.error(f"Error broadcasting message: {e}")
        return jsonify({
            'success': False,
            'error': '無法發送廣播',
            'message': str(e)
        }), 500


# ============================================================================
# Curation & Triage APIs
# ============================================================================

@staff_actions_bp.route('/api/v1/curation/triage', methods=['GET'])
def get_curation_triage():
    """取得自動分流的數據審核列表"""
    staff_id, error, status = require_staff_auth()
    if error: return error, status
    
    from src.services.logger_service import logger_service
    limit = request.args.get('limit', default=100, type=int)
    triage_data = logger_service.get_triage_logs(limit=limit)
    
    return jsonify({
        'success': True,
        'data': triage_data
    })

@staff_actions_bp.route('/api/v1/curation/batch_approve', methods=['POST'])
def batch_approve_curation():
    """批量核准數據"""
    staff_id, error, status = require_staff_auth()
    if error: return error, status
    
    data = request.get_json()
    items = data.get('items', []) # List of full log entries
    
    from src.services.logger_service import logger_service
    success_count = 0
    for item in items:
        # Assuming the UI passes back the corrected response (or original if approved as is)
        user_prompt = item['messages'][0]['content']
        ai_response = item['messages'][1]['content']
        if logger_service.save_correction(item, ai_response):
            success_count += 1
            
    return jsonify({
        'success': True,
        'approved_count': success_count
    })

@staff_actions_bp.route('/api/v1/curation/suggest_correction', methods=['POST'])
def suggest_curation_correction():
    """使用 AI + 聯網搜尋生成建議的修正版本"""
    staff_id, error, status = require_staff_auth()
    if error: return error, status

    data = request.get_json()
    user_prompt = data.get('prompt')
    current_answer = data.get('current_answer')
    route = data.get('route', 'general')

    if not user_prompt:
        return jsonify({'success': False, 'error': 'Missing prompt'}), 400

    from src.llm_server import llm_instance
    from src.services.search_service import search_service

    # 1. Perform Web Search for Grounding
    search_query = f"{user_prompt} 台灣 醫學 建議"
    search_results = search_service.search(search_query, max_results=3)
    search_context = "\n".join([f"- {r['title']}: {r['body']}" for r in search_results]) if search_results else "無外部搜尋資料。"

    # 2. Structure Prompt for Synthesis
    if route == "special":
        system_instruction = "你是一個資深的診所顧問。請結合「內部準則」與「外部搜尋參考」，優化以下回答。確保資訊極度精準且嚴禁報價。"
    else:
        system_instruction = "你是一個權威的醫學健康 AI 助理。請結合「醫學知識」與「外部最新搜尋資料」，提供一個專業、嚴謹且具備高度衛教價值的繁體中文修正版本。"

    prompt = f"""
【使用者提問】
{user_prompt}

【目前初步回答】
{current_answer}

【聯網搜尋參考資料】
{search_context}

請彙整以上資訊，提供一個更完美、更具備深度且正確的修正版本：
"""
    try:
        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ]
        suggestion = llm_instance.chat_generate(messages, max_tokens=1024).strip()
        if "<think>" in suggestion: suggestion = suggestion.split("</think>")[-1].strip()

        return jsonify({
            'success': True,
            'suggestion': suggestion,
            'has_searched': True
        })
    except Exception as e:
        logger.error(f"AI Suggestion failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# Patient CRM & History APIs
# ============================================================================

@staff_actions_bp.route('/api/v1/patient/<int:patient_id>/profile', methods=['GET'])
def get_patient_profile(patient_id):
    """取得病患詳細檔案與歷史對話"""
    staff_id, error, status = require_staff_auth()
    if error: return error, status
    
    from src.services.patient_service import PatientService
    from config.settings import DATA_DIR
    import glob
    
    service = PatientService()
    try:
        patient = service.get_patient_by_id(patient_id)
        if not patient:
            return jsonify({'success': False, 'error': 'Patient not found'}), 404
            
        # Get Platform Mappings (LINE/Messenger IDs)
        # Search in clinic.db mappings table
        his = get_his_connection()
        mappings = his.execute("SELECT line_user_id FROM line_user_mapping WHERE patient_id = ?", (patient_id,))
        platform_ids = [m['line_user_id'] for m in mappings]
        
        # Aggregate History from JSONL Logs
        history = []
        log_files = glob.glob(os.path.join(DATA_DIR, "interactions_*.jsonl"))
        
        for log_file in log_files:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if not line.strip(): continue
                        log_entry = json.loads(line)
                        # Match if the user_id in log is one of the patient's platform IDs
                        if log_entry.get('user_id') in platform_ids:
                            history.append(log_entry)
            except: continue
            
        # Sort history by timestamp
        history.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return jsonify({
            'success': True,
            'patient': patient,
            'history': history,
            'platform_ids': platform_ids
        })
    except Exception as e:
        logger.error(f"Failed to fetch patient profile: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@staff_actions_bp.route('/dashboard/staff/patient/<int:patient_id>')
def patient_detail_page(patient_id):
    """Render patient detail/history page"""
    from flask import render_template
    return render_template('staff_patient_detail.html', patient_id=patient_id)
def approvals_page():
    """Render approvals page"""
    from flask import render_template
    return render_template('staff_approvals.html')


@staff_actions_bp.route('/dashboard/staff/appointments/')
def appointments_page():
    """Render appointments page"""
    from flask import render_template
    return render_template('staff_appointments.html')


@staff_actions_bp.route('/dashboard/staff/messages/send')
def messages_page():
    """Render message send page"""
    from flask import render_template
    return render_template('staff_messages.html')