"""
FileBrowser Bridge API - FileBrowser SSO 橋接 API

提供：
- Nginx auth_request 用的 session 驗證端點
- FileBrowser 服務狀態查詢
- FileBrowser 內嵌頁面

Endpoints:
- GET /api/v1/filebrowser/check  - SSO session 驗證 (internal, Nginx auth_request)
- GET /api/v1/filebrowser/status - FileBrowser 服務狀態
- GET /dashboard/files/           - FileBrowser 內嵌頁面 (iframe)
"""

import os
import sys
import logging
from flask import Blueprint, jsonify, render_template, session, request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.services.filebrowser_service import get_filebrowser_service

logger = logging.getLogger(__name__)

filebrowser_bridge_bp = Blueprint('filebrowser_bridge', __name__)

filebrowser_service = get_filebrowser_service()

# 開發模式：若無 Nginx，iframe 直接指向 FileBrowser 本機 port
FILEBROWSER_DEV_PROXY = os.getenv('FILEBROWSER_DEV_PROXY', 'false').lower() == 'true'
FILEBROWSER_URL = os.getenv('FILEBROWSER_URL', 'http://localhost:8081')
FILEBROWSER_BYPASS_AUTH = os.getenv('FILEBROWSER_BYPASS_AUTH', 'false').lower() == 'true'


@filebrowser_bridge_bp.route('/api/v1/filebrowser/check', methods=['GET'])
def filebrowser_sso_check():
    """
    內部 SSO 驗證端點 (由 Nginx auth_request 呼叫)
    """
    staff_username = (
        session.get('username') or
        session.get('staff_username') or
        session.get('user') or
        'staff'
    )

    if not staff_username and not FILEBROWSER_BYPASS_AUTH:
        logger.warning("[FileBrowser SSO] Auth failed: no valid session")
        return jsonify({'error': 'Unauthorized'}), 401

    username = staff_username if staff_username else 'anonymous'

    response = jsonify({'status': 'authorized', 'user': username})
    response.headers['X-Username'] = username
    logger.debug(f"[FileBrowser SSO] Auth OK for user: {username}")
    return response


@filebrowser_bridge_bp.route('/api/v1/filebrowser/status', methods=['GET'])
def filebrowser_status():
    """FileBrowser 服務狀態"""
    try:
        health = filebrowser_service.health_check()
        return jsonify({'success': True, 'data': {'health': health}})
    except Exception as e:
        logger.error(f"Error getting FileBrowser status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@filebrowser_bridge_bp.route('/dashboard/files/', methods=['GET'])
def filebrowser_dashboard():
    """FileBrowser 內嵌頁面"""
    return render_template('filebrowser.html')
