"""
External Channels API - Task 12.2

Manages reviews and comments from external platforms (Google Maps, FB, Web).
Allows staff to review, edit, and approve AI-generated replies.
"""

import os
import sqlite3
import logging
from datetime import datetime
from flask import Blueprint, jsonify, request, render_template

logger = logging.getLogger(__name__)

external_channels_bp = Blueprint('external_channels', __name__)

DB_PATH = "data/db/clinic.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@external_channels_bp.route('/dashboard/external-comments/')
@external_channels_bp.route('/dashboard/external-comments')
def external_comments_dashboard():
    """多通路評論管理頁面"""
    return render_template('external_comments.html')

@external_channels_bp.route('/api/v1/external/list', methods=['GET'])
def list_external_comments():
    """取得外部評論列表"""
    try:
        status = request.args.get('status', 'pending')
        conn = get_db_connection()
        query = "SELECT * FROM external_comments WHERE status = ? ORDER BY created_at DESC"
        rows = conn.execute(query, (status,)).fetchall()
        conn.close()
        return jsonify({'success': True, 'data': [dict(r) for r in rows]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@external_channels_bp.route('/api/v1/external/approve', methods=['POST'])
def approve_reply():
    """核准並發送 AI 回覆"""
    try:
        data = request.get_json()
        comment_id = data.get('id')
        reply_text = data.get('reply_text')
        
        if not comment_id or not reply_text:
            return jsonify({'success': False, 'error': 'Missing ID or reply text'}), 400

        conn = get_db_connection()
        comment = conn.execute("SELECT * FROM external_comments WHERE id = ?", (comment_id,)).fetchone()
        
        if not comment:
            return jsonify({'success': False, 'error': 'Comment not found'}), 404

        # Route based on platform
        success = False
        platform = comment['platform']
        
        if platform == 'google_maps':
            from src.services.google_maps_service import google_maps_service
            success = google_maps_service.post_reply(comment['external_id'], reply_text)
        elif platform == 'web':
            # For web, just mark as replied (assume it's displayed on site)
            conn.execute("UPDATE external_comments SET status='replied', ai_draft_reply=?, replied_at=CURRENT_TIMESTAMP WHERE id=?", (reply_text, comment_id))
            conn.commit()
            success = True
        else:
            return jsonify({'success': False, 'error': f'Platform {platform} not supported for auto-reply yet'}), 400

        conn.close()
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@external_channels_bp.route('/api/v1/external/submit_web_comment', methods=['POST'])
def submit_web_comment():
    """
    接收來自官網的留言
    """
    try:
        data = request.get_json()
        author = data.get('name', 'Anonymous')
        content = data.get('content')
        
        if not content:
            return jsonify({'success': False, 'error': 'Content is required'}), 400

        # 1. Generate AI Draft
        from src.agent.hermes_core import get_hermes_agent
        agent = get_hermes_agent()
        prompt = f"你是一個專業的診所小編。收到官網留言：『{content}』。請寫一段溫暖且專業的建議回覆（繁體中文）。"
        draft_reply, _, _, _ = agent.chat(prompt)
        
        # 2. Save to DB
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO external_comments (platform, author_name, content, ai_draft_reply, status)
            VALUES ('web', ?, ?, ?, 'pending')
        """, (author, content, draft_reply))
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': 'Comment submitted and queued for review'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@external_channels_bp.route('/api/v1/external/sync', methods=['POST'])
def trigger_sync():
    """手動觸發 Google 評論同步"""
    try:
        from src.services.google_maps_service import google_maps_service
        count = google_maps_service.fetch_and_process_reviews()
        return jsonify({'success': True, 'message': f'已同步，發現 {count} 則新評論'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
