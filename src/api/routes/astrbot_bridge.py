"""
AstrBot Bridge API - AstrBot 橋接 API

提供 AstrBot 聊天機器人的監控和控制端點

Endpoints:
- GET  /api/v1/astrbot/status - AstrBot 健康狀態與已啟動平台
- GET  /api/v1/astrbot/sessions - 活躍聊天會話列表
- POST /api/v1/astrbot/send - 發送 IM 訊息
- GET  /dashboard/astrbot/ - AstrBot 管理儀表板頁面
"""

import os
import sys
import logging
from flask import Blueprint, jsonify, request, render_template

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.services.astrbot_service import get_astrbot_service

logger = logging.getLogger(__name__)

astrbot_bridge_bp = Blueprint('astrbot_bridge', __name__)

astrbot_service = get_astrbot_service()


@astrbot_bridge_bp.route('/api/v1/astrbot/status', methods=['GET'])
def astrbot_status():
    """AstrBot 健康狀態與已啟動平台列表"""
    try:
        health = astrbot_service.health_check()
        bots_result = astrbot_service.get_bots()

        return jsonify({
            'success': True,
            'data': {
                'health': health,
                'bots': bots_result.get('data', []) if bots_result.get('success') else [],
                'bots_error': None if bots_result.get('success') else bots_result.get('error'),
            }
        })
    except Exception as e:
        logger.error(f"Error getting AstrBot status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@astrbot_bridge_bp.route('/api/v1/astrbot/sessions', methods=['GET'])
def astrbot_sessions():
    """活躍聊天會話列表"""
    try:
        result = astrbot_service.get_sessions()
        if result.get('success'):
            sessions = result.get('data', [])
            if isinstance(sessions, dict):
                sessions = list(sessions.values()) if 'sessions' in sessions else [sessions]
            return jsonify({'success': True, 'data': sessions})
        return jsonify({'success': False, 'error': result.get('error', 'Failed to get sessions')}), 502
    except Exception as e:
        logger.error(f"Error getting AstrBot sessions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@astrbot_bridge_bp.route('/api/v1/astrbot/send', methods=['POST'])
def astrbot_send():
    """發送 IM 訊息
    Body: { "platform": "qq_official", "target": "user_id", "content": "Hello" }
    """
    try:
        body = request.get_json()
        if not body:
            return jsonify({'success': False, 'error': 'Missing request body'}), 400

        platform = body.get('platform')
        target = body.get('target')
        content = body.get('content')

        if not all([platform, target, content]):
            return jsonify({'success': False, 'error': 'Missing platform, target, or content'}), 400

        result = astrbot_service.send_message(platform, target, content)
        if result.get('success'):
            return jsonify({'success': True, 'data': result.get('data')})
        return jsonify({'success': False, 'error': result.get('error', 'Send failed')}), 502
    except Exception as e:
        logger.error(f"Error sending AstrBot message: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@astrbot_bridge_bp.route('/dashboard/astrbot/', methods=['GET'])
def astrbot_dashboard():
    """AstrBot 管理儀表板頁面"""
    return render_template('astrbot_dashboard.html')
