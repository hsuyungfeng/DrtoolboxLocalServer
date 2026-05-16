"""
Staff Conversation Thread View (Task 4.3 - Phase 4)

Provides authenticated endpoint for staff to view a full conversation thread:
  - GET /dashboard/staff/conversation/<int:patient_id> — Renders thread UI
  - GET /api/staff/conversation/<int:patient_id> — JSON API for polling new messages

Features:
  - Displays full conversation history (patient and bot messages)
  - Auto-marks messages as read upon viewing
  - Staff authentication via X-Staff-ID header (or staff_id query param for UI)
"""

import logging
import sqlite3
from datetime import datetime
from functools import wraps
from flask import Blueprint, request, jsonify, render_template

logger = logging.getLogger(__name__)

staff_conversation_bp = Blueprint("staff_conversation", __name__)

def _get_db_connection():
    """Get database connection with row factory."""
    conn = sqlite3.connect('data/db/clinic.db')
    conn.row_factory = sqlite3.Row
    return conn

def require_staff_id_or_param(f):
    """Decorator to require staff ID from header or query param."""
    @wraps(f)
    def decorated(*args, **kwargs):
        staff_id = request.headers.get('X-Staff-ID', '').strip()
        if not staff_id:
            staff_id = request.args.get('staff_id', '').strip()
            
        if not staff_id:
            logger.warning("Unauthenticated access attempt | path=%s", request.path)
            return jsonify({'error': 'X-Staff-ID header or staff_id parameter required'}), 401

        return f(*args, staff_id=staff_id, **kwargs)
    return decorated

@staff_conversation_bp.route('/dashboard/staff/conversation/<int:patient_id>', methods=['GET'])
@require_staff_id_or_param
def view_conversation(patient_id, staff_id):
    """Render the conversation thread UI for a specific patient."""
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get patient info
            cursor.execute('SELECT patient_id, name, phone FROM patients WHERE patient_id = ?', (patient_id,))
            patient = cursor.fetchone()
            if not patient:
                return "Patient not found", 404
                
            # Get conversation history
            cursor.execute('''
                SELECT * 
                FROM patient_conversations 
                WHERE patient_id = ? 
                ORDER BY timestamp ASC
            ''', (str(patient_id),))
            messages = cursor.fetchall()
            
            # Check if there's any unread message
            cursor.execute('''
                SELECT COUNT(*) as cnt 
                FROM patient_conversations 
                WHERE patient_id = ? AND unread_flag = 1
            ''', (str(patient_id),))
            has_unread = cursor.fetchone()['cnt'] > 0
            
            # Mark messages as read automatically
            if has_unread:
                cursor.execute('''
                    UPDATE patient_conversations
                    SET unread_flag = 0
                    WHERE patient_id = ? AND unread_flag = 1
                ''', (str(patient_id),))
                conn.commit()
                logger.info("Marked messages as read | staff_id=%s patient_id=%s", staff_id, patient_id)
            
        return render_template('staff_conversation.html', 
                             patient=patient, 
                             messages=messages,
                             staff_id=staff_id)
                             
    except sqlite3.Error as e:
        logger.error("Database error in view_conversation: %s", str(e))
        return "Database Error", 500
    except Exception as e:
        logger.error("Error loading conversation: %s", str(e))
        return "Internal Error", 500


@staff_conversation_bp.route('/api/staff/conversation/<int:patient_id>', methods=['GET'])
@require_staff_id_or_param
def get_conversation_api(patient_id, staff_id):
    """JSON API to fetch conversation messages, used for polling."""
    try:
        since = request.args.get('since') # ISO timestamp
        
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = 'SELECT * FROM patient_conversations WHERE patient_id = ?'
            params = [str(patient_id)]
            
            if since:
                query += ' AND timestamp > ?'
                params.append(since)
                
            query += ' ORDER BY timestamp ASC'
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            messages = []
            for row in rows:
                messages.append({
                    'id': row['id'],
                    'message_id': row['message_id'],
                    'sender': row['sender'],
                    'text': row['text'],
                    'timestamp': row['timestamp'],
                    'rag_confidence': row['rag_confidence'],
                    'escalated_flag': bool(row['escalated_flag'])
                })
                
            # Mark as read if any new messages are fetched
            if messages:
                cursor.execute('''
                    UPDATE patient_conversations
                    SET unread_flag = 0
                    WHERE patient_id = ? AND unread_flag = 1
                ''', (str(patient_id),))
                conn.commit()
            
            return jsonify({
                'patient_id': patient_id,
                'messages': messages,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            })
            
    except sqlite3.Error as e:
        logger.error("Database error in get_conversation_api: %s", str(e))
        return jsonify({'error': 'Database error'}), 500
    except Exception as e:
        logger.error("Error in get_conversation_api: %s", str(e))
        return jsonify({'error': 'Internal error'}), 500
