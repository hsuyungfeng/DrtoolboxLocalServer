"""
Analytics API - 提供診所分析數據 API

Endpoints:
- GET /api/v1/analytics/overview - 診所概覽數據
- GET /api/v1/analytics/messages - 訊息趨勢數據
- GET /api/v1/analytics/patients - 患者統計數據
- GET /api/v1/analytics/appointments - 預約統計
"""

import os
import sys
import sqlite3
import logging
from datetime import datetime, timedelta
from flask import Blueprint, jsonify

# Fix import paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

logger = logging.getLogger(__name__)

# Create Blueprint
analytics_bp = Blueprint('analytics', __name__)

# Database path
DB_PATH = os.environ.get('CLINIC_DB_PATH', os.path.join(os.path.dirname(__file__), '../../../db/clinic.db'))


def get_db_connection():
    """取得資料庫連線"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@analytics_bp.route('/api/v1/analytics/overview', methods=['GET'])
def get_overview():
    """取得診所概覽數據"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 總患者數
        cursor.execute('SELECT COUNT(*) as count FROM patients')
        total_patients = cursor.fetchone()['count']

        # 本月新患者
        cursor.execute('''
            SELECT COUNT(*) as count FROM patients
            WHERE strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')
        ''')
        new_patients_this_month = cursor.fetchone()['count']

        # 本月訊息數
        cursor.execute('''
            SELECT COUNT(*) as count FROM patient_conversations
            WHERE strftime('%Y-%m', timestamp) = strftime('%Y-%m', 'now')
        ''')
        messages_this_month = cursor.fetchone()['count']

        # 待處理升級數
        cursor.execute('''
            SELECT COUNT(*) as count FROM patient_conversations
            WHERE escalated_flag = 1
        ''')
        pending_escalations = cursor.fetchone()['count']

        conn.close()

        return jsonify({
            'success': True,
            'timestamp': datetime.utcnow().isoformat(),
            'data': {
                'total_patients': total_patients,
                'new_patients_this_month': new_patients_this_month,
                'messages_this_month': messages_this_month,
                'pending_escalations': pending_escalations
            }
        })

    except Exception as e:
        logger.error(f"Error getting analytics overview: {e}")
        return jsonify({
            'success': False,
            'error': '無法取得分析數據',
            'message': str(e)
        }), 500


@analytics_bp.route('/api/v1/analytics/messages', methods=['GET'])
def get_message_trends():
    """取得訊息趨勢數據（過去7天）"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 過去7天的每日訊息數
        days_data = []
        for i in range(6, -1, -1):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            cursor.execute('''
                SELECT COUNT(*) as count FROM patient_conversations
                WHERE date(timestamp) = ?
            ''', (date,))
            count = cursor.fetchone()['count']
            days_data.append({
                'date': date,
                'count': count
            })

        # 頻道分布（LINE vs 網頁）
        # 預設都是網頁，因為系統沒有明確的頻道欄位
        channel_distribution = {
            'web': sum(d['count'] for d in days_data),
            'line': 0
        }

        conn.close()

        return jsonify({
            'success': True,
            'timestamp': datetime.utcnow().isoformat(),
            'data': {
                'daily_messages': days_data,
                'channel_distribution': channel_distribution
            }
        })

    except Exception as e:
        logger.error(f"Error getting message trends: {e}")
        return jsonify({
            'success': False,
            'error': '無法取得訊息趨勢',
            'message': str(e)
        }), 500


@analytics_bp.route('/api/v1/analytics/patients', methods=['GET'])
def get_patient_stats():
    """取得患者統計數據"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 患者總數
        cursor.execute('SELECT COUNT(*) as count FROM patients')
        total = cursor.fetchone()['count']

        # 計算年齡分布
        # 這裡我們使用一個簡化的方法，假設有 birthday 欄位
        age_distribution = {
            '0-17': 0,
            '18-30': 0,
            '31-45': 0,
            '46-60': 0,
            '60+': 0
        }

        # 依賴度分布（基於訊息數量估算）
        # 高依賴：10+ 訊息, 中依賴：3-9 訊息, 低依賴：0-2 訊息
        dependency_distribution = {
            'high': 0,
            'medium': 0,
            'low': total  # 預設為低
        }

        cursor.execute('''
            SELECT patient_id FROM patients
        ''')
        patients = cursor.fetchall()

        for patient in patients:
            patient_id = patient['patient_id']
            cursor.execute('''
                SELECT COUNT(*) as count FROM patient_conversations
                WHERE patient_id = ?
            ''', (str(patient_id),))
            msg_count = cursor.fetchone()['count']

            if msg_count >= 10:
                dependency_distribution['high'] += 1
            elif msg_count >= 3:
                dependency_distribution['medium'] += 1

        # 調整低依賴度
        dependency_distribution['low'] = total - dependency_distribution['high'] - dependency_distribution['medium']

        conn.close()

        return jsonify({
            'success': True,
            'timestamp': datetime.utcnow().isoformat(),
            'data': {
                'total_patients': total,
                'age_distribution': age_distribution,
                'dependency_distribution': dependency_distribution
            }
        })

    except Exception as e:
        logger.error(f"Error getting patient stats: {e}")
        return jsonify({
            'success': False,
            'error': '無法取得患者統計',
            'message': str(e)
        }), 500


@analytics_bp.route('/api/v1/analytics/appointments', methods=['GET'])
def get_appointment_stats():
    """取得預約統計"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        today = datetime.now().strftime('%Y-%m-%d')
        week_end = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')

        # 今日預約
        cursor.execute('''
            SELECT COUNT(*) as count FROM appointments
            WHERE date(appointment_date) = ?
        ''', (today,))
        today_appointments = cursor.fetchone()['count']

        # 本週預約
        cursor.execute('''
            SELECT COUNT(*) as count FROM appointments
            WHERE date(appointment_date) >= ? AND date(appointment_date) <= ?
        ''', (today, week_end))
        week_appointments = cursor.fetchone()['count']

        # 已完成 vs 總預約（完成率）
        cursor.execute('SELECT COUNT(*) as count FROM appointments')
        total_appointments = cursor.fetchone()['count']

        cursor.execute('''
            SELECT COUNT(*) as count FROM appointments
            WHERE status = 'completed'
        ''')
        completed_appointments = cursor.fetchone()['count']

        completion_rate = (completed_appointments / total_appointments * 100) if total_appointments > 0 else 0

        conn.close()

        return jsonify({
            'success': True,
            'timestamp': datetime.utcnow().isoformat(),
            'data': {
                'today_appointments': today_appointments,
                'week_appointments': week_appointments,
                'total_appointments': total_appointments,
                'completed_appointments': completed_appointments,
                'completion_rate': round(completion_rate, 1)
            }
        })

    except Exception as e:
        logger.error(f"Error getting appointment stats: {e}")
        return jsonify({
            'success': False,
            'error': '無法取得預約統計',
            'message': str(e)
        }), 500


@analytics_bp.route('/dashboard/analytics/')
def analytics_dashboard():
    """Render analytics dashboard page"""
    from flask import render_template
    return render_template('analytics_dashboard.html')