"""
Chat Monitor API — LLM 與患者對話監控

提供即時監控 LLM chatbot 與患者之間的對話狀態

Endpoints:
- GET  /api/v1/chat-monitor/conversations — 所有活躍對話摘要 (含最新訊息)
- GET  /api/v1/chat-monitor/conversation/<patient_id> — 單一患者完整對話
- GET  /api/v1/chat-monitor/stats — 對話統計 (總數、信心度、升級率)
- GET  /dashboard/chat-monitor/ — 對話監控儀表板頁面
"""

import os
import sys
import sqlite3
import logging
from flask import Blueprint, jsonify, render_template, request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

logger = logging.getLogger(__name__)

chat_monitor_bp = Blueprint('chat_monitor', __name__)

DB_PATH = os.environ.get('CLINIC_DB_PATH', os.path.join(os.path.dirname(__file__), '../../../clinic.db'))


def _get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@chat_monitor_bp.route('/api/v1/chat-monitor/conversations', methods=['GET'])
def list_conversations():
    """所有活躍對話摘要 — 按患者分組，顯示最新訊息與狀態"""
    try:
        conn = _get_db()
        rows = conn.execute("""
            SELECT 
                patient_id,
                COUNT(*) as msg_count,
                MAX(timestamp) as last_msg_time,
                AVG(CASE WHEN sender='bot' THEN rag_confidence ELSE NULL END) as avg_confidence,
                SUM(CASE WHEN escalated_flag=1 THEN 1 ELSE 0 END) as escalated_count,
                SUM(CASE WHEN unread_flag=1 THEN 1 ELSE 0 END) as unread_count
            FROM patient_conversations
            GROUP BY patient_id
            ORDER BY last_msg_time DESC
            LIMIT 50
        """).fetchall()

        conversations = []
        for row in rows:
            # 取得每位患者最新一條訊息
            last_msg = conn.execute("""
                SELECT sender, text, timestamp, rag_confidence, escalated_flag
                FROM patient_conversations
                WHERE patient_id = ?
                ORDER BY timestamp DESC LIMIT 1
            """, (row['patient_id'],)).fetchone()

            conversations.append({
                'patient_id': row['patient_id'],
                'msg_count': row['msg_count'],
                'last_msg_time': row['last_msg_time'],
                'avg_confidence': round(row['avg_confidence'] * 100, 1) if row['avg_confidence'] else None,
                'escalated_count': row['escalated_count'],
                'unread_count': row['unread_count'],
                'last_sender': last_msg['sender'] if last_msg else None,
                'last_text': last_msg['text'][:100] if last_msg else None,
                'last_confidence': round(last_msg['rag_confidence'] * 100, 1) if last_msg and last_msg['rag_confidence'] else None,
                'last_escalated': bool(last_msg['escalated_flag']) if last_msg else False,
            })

        conn.close()
        return jsonify({'success': True, 'data': conversations})
    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@chat_monitor_bp.route('/api/v1/chat-monitor/conversation/<patient_id>', methods=['GET'])
def get_conversation(patient_id):
    """取得單一患者的完整對話歷史"""
    try:
        conn = _get_db()
        rows = conn.execute("""
            SELECT id, patient_id, message_id, sender, text, timestamp,
                   rag_confidence, escalated_flag, unread_flag
            FROM patient_conversations
            WHERE patient_id = ?
            ORDER BY timestamp ASC
            LIMIT 200
        """, (patient_id,)).fetchall()

        messages = [dict(r) for r in rows]

        # 標記已讀
        conn.execute("""
            UPDATE patient_conversations SET unread_flag = 0
            WHERE patient_id = ? AND unread_flag = 1
        """, (patient_id,))
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'data': messages})
    except Exception as e:
        logger.error(f"Error getting conversation for {patient_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@chat_monitor_bp.route('/api/v1/chat-monitor/stats', methods=['GET'])
def get_stats():
    """對話統計摘要"""
    try:
        conn = _get_db()
        total = conn.execute("SELECT COUNT(*) as cnt FROM patient_conversations").fetchone()['cnt']
        escalated = conn.execute("SELECT COUNT(*) as cnt FROM patient_conversations WHERE escalated_flag = 1").fetchone()['cnt']
        unread = conn.execute("SELECT COUNT(*) as cnt FROM patient_conversations WHERE unread_flag = 1").fetchone()['cnt']
        active_patients = conn.execute(
            "SELECT COUNT(DISTINCT patient_id) as cnt FROM patient_conversations"
        ).fetchone()['cnt']

        avg_conf = conn.execute(
            "SELECT AVG(rag_confidence) as c FROM patient_conversations WHERE sender='bot' AND rag_confidence IS NOT NULL"
        ).fetchone()['c']

        conn.close()
        return jsonify({'success': True, 'data': {
            'total_messages': total,
            'escalated': escalated,
            'unread': unread,
            'active_patients': active_patients,
            'avg_confidence': round(avg_conf * 100, 1) if avg_conf else 0,
        }})
    except Exception as e:
        logger.error(f"Error getting chat stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@chat_monitor_bp.route('/dashboard/chat-monitor/', methods=['GET'])
def chat_monitor_dashboard():
    """對話監控儀表板頁面"""
    return render_template('chat_monitor.html')
