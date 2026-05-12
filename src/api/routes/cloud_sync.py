"""
Cloud Sync API - 雲端同步 API

提供與 doctor-toolbox.com 的雙向資料同步端點

Endpoints:
- POST /api/v1/sync/patient - 同步單一患者至雲端
- POST /api/v1/sync/patients/bulk - 批量同步患者
- POST /api/v1/sync/analytics - 手動觸發分析數據同步
- GET /api/v1/sync/status - 取得同步狀態
- GET /api/v1/sync/logs - 取得同步日誌
- GET /api/v1/sync/config - 取得同步配置
- PUT /api/v1/sync/config - 更新同步配置
"""

import os
import sys
import sqlite3
import logging
import uuid
from flask import Blueprint, jsonify, request

# Fix import paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.services.cloud_sync_service import get_cloud_sync_service

logger = logging.getLogger(__name__)

# Create Blueprint
cloud_sync_bp = Blueprint('cloud_sync', __name__)

# Initialize service
cloud_sync_service = get_cloud_sync_service()

# Database path
DB_PATH = os.environ.get('CLINIC_DB_PATH', os.path.join(os.path.dirname(__file__), '../../../db/clinic.db'))


def get_db_connection():
    """Get database connection"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class DBContext:
    """Context manager for guaranteed database connection cleanup"""
    def __enter__(self):
        self.conn = get_db_connection()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()
        return False


# ============================================================================
# Patient Sync APIs (患者資料同步)
# ============================================================================

@cloud_sync_bp.route('/api/v1/sync/patient', methods=['POST'])
def sync_patient():
    """
    同步單一患者至雲端

    Request Body:
        patient_id: int (required)

    Returns:
        {success: bool, sync_id: int, message: str}
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'error': '需要提供患者資料'
            }), 400

        patient_id = data.get('patient_id')

        if not patient_id:
            return jsonify({
                'success': False,
                'error': '需要患者 ID'
            }), 400

        result = cloud_sync_service.sync_patient_data(patient_id)

        # 添加 request_id 用於追蹤
        result['request_id'] = str(uuid.uuid4())

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in sync_patient: {e}")
        return jsonify({
            'success': False,
            'error': '同步失敗',
            'message': str(e),
            'request_id': str(uuid.uuid4())
        }), 500


@cloud_sync_bp.route('/api/v1/sync/patients/bulk', methods=['POST'])
def sync_patients_bulk():
    """
    批量同步患者至雲端

    Request Body:
        patient_ids: list[int] (optional, if empty sync all)

    Returns:
        {success: bool, synced_count: int, failed_count: int}
    """
    try:
        data = request.get_json() or {}
        patient_ids = data.get('patient_ids', [])

        # 如果沒有指定患者 ID，則同步所有患者
        if not patient_ids:
            with DBContext() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT patient_id FROM patients')
                patient_ids = [row[0] for row in cursor.fetchall()]

        synced_count = 0
        failed_count = 0

        for patient_id in patient_ids:
            result = cloud_sync_service.sync_patient_data(patient_id)
            if result['success']:
                synced_count += 1
            else:
                failed_count += 1

        logger.info(
            f"[Cloud Sync Stub] Bulk sync completed: "
            f"synced={synced_count}, failed={failed_count}"
        )

        return jsonify({
            'success': True,
            'message': f'批量同步完成（Stub 模式）',
            'data': {
                'synced_count': synced_count,
                'failed_count': failed_count,
                'request_id': str(uuid.uuid4())
            }
        })

    except Exception as e:
        logger.error(f"Error in sync_patients_bulk: {e}")
        return jsonify({
            'success': False,
            'error': '批量同步失敗',
            'message': str(e),
            'request_id': str(uuid.uuid4())
        }), 500


# ============================================================================
# Analytics Sync API (分析數據同步)
# ============================================================================

@cloud_sync_bp.route('/api/v1/sync/analytics', methods=['POST'])
def sync_analytics():
    """
    手動觸發分析數據同步

    Returns:
        {success: bool, sync_id: int, message: str}
    """
    try:
        result = cloud_sync_service.sync_analytics_data()

        # 添加 request_id 用於追蹤
        result['request_id'] = str(uuid.uuid4())

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in sync_analytics: {e}")
        return jsonify({
            'success': False,
            'error': '分析數據同步失敗',
            'message': str(e),
            'request_id': str(uuid.uuid4())
        }), 500


# ============================================================================
# Status & Logs APIs (狀態與日誌)
# ============================================================================

@cloud_sync_bp.route('/api/v1/sync/status', methods=['GET'])
def get_sync_status():
    """
    取得同步狀態

    Returns:
        {success: bool, data: {...}}
    """
    try:
        result = cloud_sync_service.get_sync_status()
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        return jsonify({
            'success': False,
            'error': '無法取得同步狀態',
            'message': str(e)
        }), 500


@cloud_sync_bp.route('/api/v1/sync/logs', methods=['GET'])
def get_sync_logs():
    """
    取得同步日誌

    Query Parameters:
        limit: int (default 50)
        offset: int (default 0)

    Returns:
        {success: bool, data: {logs: [...], total: int}}
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)

        result = cloud_sync_service.get_sync_logs(limit=limit, offset=offset)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error getting sync logs: {e}")
        return jsonify({
            'success': False,
            'error': '無法取得同步日誌',
            'message': str(e)
        }), 500


# ============================================================================
# Config APIs (配置)
# ============================================================================

@cloud_sync_bp.route('/api/v1/sync/config', methods=['GET'])
def get_sync_config():
    """
    取得同步配置

    Returns:
        {success: bool, data: {...}}
    """
    try:
        return jsonify({
            'success': True,
            'data': {
                'cloud_url': cloud_sync_service.cloud_url or '',
                'is_configured': bool(cloud_sync_service.cloud_url and cloud_sync_service.api_key),
                'sync_interval': cloud_sync_service.sync_interval
            }
        })

    except Exception as e:
        logger.error(f"Error getting sync config: {e}")
        return jsonify({
            'success': False,
            'error': '無法取得同步配置',
            'message': str(e)
        }), 500


@cloud_sync_bp.route('/api/v1/sync/config', methods=['PUT'])
def update_sync_config():
    """
    更新同步配置

    Request Body:
        cloud_url: str (optional)
        api_key: str (optional)
        sync_interval: int (optional)

    Returns:
        {success: bool, message: str}
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'error': '需要提供配置資料'
            }), 400

        # 更新配置（僅記憶體，實際應寫入資料庫或環境變數）
        if 'cloud_url' in data:
            cloud_sync_service.cloud_url = data['cloud_url']

        if 'sync_interval' in data:
            cloud_sync_service.sync_interval = int(data['sync_interval'])

        logger.info(f"[Cloud Sync Stub] Config updated: {data}")

        return jsonify({
            'success': True,
            'message': '配置已更新（Stub 模式 - 重啟後生效）',
            'data': {
                'cloud_url': cloud_sync_service.cloud_url,
                'sync_interval': cloud_sync_service.sync_interval
            }
        })

    except Exception as e:
        logger.error(f"Error updating sync config: {e}")
        return jsonify({
            'success': False,
            'error': '無法更新同步配置',
            'message': str(e)
        }), 500