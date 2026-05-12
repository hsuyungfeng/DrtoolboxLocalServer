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
DB_PATH = os.environ.get('CLINIC_DB_PATH', os.path.join(os.path.dirname(__file__), '../../../db/clinic.db'))


def get_db_connection():
    """取得資料庫連線"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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
        conn = get_db_connection()
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

        conn.close()

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

        conn = get_db_connection()
        cursor = conn.cursor()

        # 更新為已處理
        cursor.execute('''
            UPDATE patient_conversations
            SET escalated_flag = 0
            WHERE id = ?
        ''', (escalation_id,))

        conn.commit()
        conn.close()

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

        conn = get_db_connection()
        cursor = conn.cursor()

        # 標記為已處理（不解釋原因）
        cursor.execute('''
            UPDATE patient_conversations
            SET escalated_flag = 0
            WHERE id = ?
        ''', (escalation_id,))

        conn.commit()
        conn.close()

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

        conn = get_db_connection()
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

        conn.close()

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
        notes = data.get('notes', '')

        if not patient_id or not appointment_date:
            return jsonify({
                'success': False,
                'error': '需要患者 ID 和預約日期'
            }), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO appointments (patient_id, appointment_date, status, created_by, updated_by)
            VALUES (?, ?, 'pending', ?, ?)
        ''', (patient_id, appointment_date, staff_id, staff_id))

        appointment_id = cursor.lastrowid
        conn.commit()
        conn.close()

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

        conn = get_db_connection()
        cursor = conn.cursor()

        # 構建更新語句
        updates = []
        params = []

        if 'appointment_date' in data:
            updates.append('appointment_date = ?')
            params.append(data['appointment_date'])

        if 'status' in data:
            updates.append('status = ?')
            params.append(data['status'])

        if updates:
            updates.append('updated_by = ?')
            params.append(staff_id)
            updates.append('updated_at = CURRENT_TIMESTAMP')

            params.append(appointment_id)
            query = f'UPDATE appointments SET {", ".join(updates)} WHERE appointment_id = ?'
            cursor.execute(query, params)
            conn.commit()

        conn.close()

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
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE appointments
            SET status = 'cancelled', updated_by = ?, updated_at = CURRENT_TIMESTAMP
            WHERE appointment_id = ?
        ''', (staff_id, appointment_id))

        conn.commit()
        conn.close()

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

        if len(message_text) > 1000:
            return jsonify({
                'success': False,
                'error': '訊息內容不能超過 1000 字'
            }), 400

        # 儲存訊息到對話歷史
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO patient_conversations
            (patient_id, sender, text, rag_confidence, escalated_flag)
            VALUES (?, 'staff', ?, NULL, 0)
        ''', (patient_id, message_text))

        message_id = cursor.lastrowid
        conn.commit()
        conn.close()

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

        conn = get_db_connection()
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
        conn.close()

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
# Page Routes (員工頁面)
# ============================================================================

@staff_actions_bp.route('/dashboard/staff/approvals/')
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