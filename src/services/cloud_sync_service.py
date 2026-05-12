"""
Cloud Sync Service - 雲端同步服務

提供與 doctor-toolbox.com 的雙向資料同步功能

主要功能：
- sync_patient_data(patient_id) - 同步單一患者資料至雲端
- sync_analytics_data() - 同步分析數據至雲端儀表板
- get_sync_status() - 取得同步狀態
- process_pending_syncs() - 處理待同步的記錄
"""

import os
import sys
import sqlite3
import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any

# Fix import paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

logger = logging.getLogger(__name__)

# Cloud sync configuration
CLOUD_SYNC_URL = os.getenv('CLOUD_SYNC_URL', '')
CLOUD_SYNC_API_KEY = os.getenv('CLOUD_SYNC_API_KEY', '')
SYNC_INTERVAL = int(os.getenv('SYNC_INTERVAL', '300'))  # 5 minutes default
MAX_RETRIES = 3

# Database path
DB_PATH = os.environ.get('CLINIC_DB_PATH', os.path.join(os.path.dirname(__file__), '../../db/clinic.db'))


def get_db_connection():
    """取得資料庫連線"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class CloudSyncService:
    """雲端同步服務"""

    def __init__(self):
        self.cloud_url = CLOUD_SYNC_URL
        self.api_key = CLOUD_SYNC_API_KEY
        self.sync_interval = SYNC_INTERVAL

    def _log_sync(self, sync_type: str, direction: str, status: str,
                   record_id: Optional[str] = None,
                   payload: Optional[Dict] = None,
                   error_message: Optional[str] = None) -> int:
        """
        記錄同步操作到 sync_logs 表

        Args:
            sync_type: 同步類型 ('patient', 'analytics', 'appointment')
            direction: 方向 ('push', 'pull')
            status: 狀態 ('pending', 'completed', 'failed')
            record_id: 記錄 ID
            payload: 同步資料
            error_message: 錯誤訊息

        Returns:
            sync log ID
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO sync_logs
                (sync_type, direction, status, record_id, payload_json, error_message, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                sync_type,
                direction,
                status,
                record_id,
                json.dumps(payload) if payload else None,
                error_message,
                datetime.utcnow().isoformat() if status in ('completed', 'failed') else None
            ))

            sync_log_id = cursor.lastrowid
            conn.commit()
            conn.close()

            return sync_log_id

        except Exception as e:
            logger.error(f"Failed to log sync: {e}")
            return -1

    def sync_patient_data(self, patient_id: int) -> Dict[str, Any]:
        """
        同步單一患者資料至雲端

        Args:
            patient_id: 患者 ID

        Returns:
            同步結果字典
        """
        logger.info(f"[Cloud Sync Stub] sync_patient_data called for patient_id={patient_id}")

        try:
            # 取得患者資料
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT patient_id, name, phone, email, dob, created_at
                FROM patients
                WHERE patient_id = ?
            ''', (patient_id,))

            row = cursor.fetchone()
            conn.close()

            if not row:
                return {
                    'success': False,
                    'error': f'患者 {patient_id} 不存在',
                    'sync_id': None
                }

            patient_data = dict(row)

            # 過濾敏感欄位（不傳輸病歷詳細資料）
            # T-05-06: 敏感欄位過濾
            safe_data = {
                'patient_id': patient_data.get('patient_id'),
                'name': patient_data.get('name'),
                'created_at': patient_data.get('created_at')
            }

            # 記錄同步日誌（Stub 模式）
            sync_log_id = self._log_sync(
                sync_type='patient',
                direction='push',
                status='completed',  # Stub 模式下視為成功
                record_id=str(patient_id),
                payload=safe_data,
                error_message=None
            )

            logger.info(
                f"[Cloud Sync Stub] Patient {patient_id} sync logged. "
                f"Cloud sync stub — 實際同步將在 production 環境啟用"
            )

            return {
                'success': True,
                'sync_id': sync_log_id,
                'message': '患者資料已同步（Stub 模式）',
                'data': safe_data
            }

        except Exception as e:
            logger.error(f"Error syncing patient {patient_id}: {e}")

            self._log_sync(
                sync_type='patient',
                direction='push',
                status='failed',
                record_id=str(patient_id),
                error_message=str(e)
            )

            return {
                'success': False,
                'error': str(e),
                'sync_id': None
            }

    def sync_analytics_data(self) -> Dict[str, Any]:
        """
        同步分析數據至雲端儀表板

        Returns:
            同步結果字典
        """
        logger.info("[Cloud Sync Stub] sync_analytics_data called")

        try:
            # 取得分析數據
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
            new_patients = cursor.fetchone()['count']

            # 本月訊息數
            cursor.execute('''
                SELECT COUNT(*) as count FROM patient_conversations
                WHERE strftime('%Y-%m', timestamp) = strftime('%Y-%m', 'now')
            ''')
            messages_count = cursor.fetchone()['count']

            conn.close()

            analytics_data = {
                'total_patients': total_patients,
                'new_patients_this_month': new_patients,
                'messages_this_month': messages_count,
                'synced_at': datetime.utcnow().isoformat()
            }

            # 記錄同步日誌（Stub 模式）
            sync_log_id = self._log_sync(
                sync_type='analytics',
                direction='push',
                status='completed',
                record_id='analytics_snapshot',
                payload=analytics_data
            )

            logger.info(
                f"[Cloud Sync Stub] Analytics sync logged. "
                f"Cloud sync stub — 實際同步將在 production 環境啟用"
            )

            return {
                'success': True,
                'sync_id': sync_log_id,
                'message': '分析數據已同步（Stub 模式）',
                'data': analytics_data
            }

        except Exception as e:
            logger.error(f"Error syncing analytics: {e}")

            self._log_sync(
                sync_type='analytics',
                direction='push',
                status='failed',
                record_id='analytics_snapshot',
                error_message=str(e)
            )

            return {
                'success': False,
                'error': str(e),
                'sync_id': None
            }

    def get_sync_status(self) -> Dict[str, Any]:
        """
        取得同步狀態

        Returns:
            同步狀態字典
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # 取得同步統計
            cursor.execute('''
                SELECT
                    sync_type,
                    status,
                    COUNT(*) as count
                FROM sync_logs
                WHERE created_at >= datetime('now', '-7 days')
                GROUP BY sync_type, status
            ''')
            stats = cursor.fetchall()

            # 取得最後同步時間
            cursor.execute('''
                SELECT sync_type, created_at, status
                FROM sync_logs
                WHERE status = 'completed'
                ORDER BY created_at DESC
            ''')
            last_syncs = cursor.fetchall()

            conn.close()

            # 格式化統計數據
            sync_stats = {}
            for row in stats:
                key = f"{row['sync_type']}_{row['status']}"
                sync_stats[key] = row['count']

            # 格式化最後同步時間
            last_sync_times = {}
            for row in last_syncs:
                if row['sync_type'] not in last_sync_times:
                    last_sync_times[row['sync_type']] = row['created_at']

            return {
                'success': True,
                'data': {
                    'sync_stats': sync_stats,
                    'last_sync_times': last_sync_times,
                    'is_configured': bool(self.cloud_url and self.api_key),
                    'cloud_url': self.cloud_url or '(未配置)',
                    'sync_interval': self.sync_interval
                }
            }

        except Exception as e:
            logger.error(f"Error getting sync status: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def process_pending_syncs(self) -> Dict[str, Any]:
        """
        處理待同步的記錄（排程任務）

        Returns:
            處理結果字典
        """
        logger.info("[Cloud Sync Stub] process_pending_syncs called")

        # Stub 模式下不做實際處理
        return {
            'success': True,
            'message': '無待處理同步（Stub 模式）',
            'processed': 0
        }

    def get_sync_logs(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """
        取得同步日誌

        Args:
            limit: 返回數量限制
            offset: 偏移量

        Returns:
            同步日誌列表
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM sync_logs
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (limit, offset))

            rows = cursor.fetchall()

            cursor.execute('SELECT COUNT(*) as count FROM sync_logs')
            total = cursor.fetchone()['count']

            conn.close()

            logs = [dict(row) for row in rows]

            return {
                'success': True,
                'data': {
                    'logs': logs,
                    'total': total,
                    'limit': limit,
                    'offset': offset
                }
            }

        except Exception as e:
            logger.error(f"Error getting sync logs: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Singleton instance
_cloud_sync_service = None


def get_cloud_sync_service() -> CloudSyncService:
    """取得或創建 CloudSyncService 單例"""
    global _cloud_sync_service
    if _cloud_sync_service is None:
        _cloud_sync_service = CloudSyncService()
    return _cloud_sync_service