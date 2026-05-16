"""
FileBrowser Service - FileBrowser 檔案管理橋接服務

提供與 FileBrowser 容器的 HTTP API 通訊，包括：
- 健康檢查
- 取得使用量統計 (磁碟使用、檔案數量)

主要功能：
- health_check() - 檢查 FileBrowser 服務狀態
- get_usage_stats() - 取得儲存使用統計
"""

import os
import sys
import json
import logging
import urllib.request
import urllib.error
from typing import Optional, Dict, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

logger = logging.getLogger(__name__)


class FileBrowserService:
    """FileBrowser API 橋接服務"""

    def __init__(self):
        self.base_url = os.getenv('FILEBROWSER_URL', 'http://localhost:8081')
        self.timeout = 5

    def _request(self, method: str, path: str, body: dict = None) -> Dict[str, Any]:
        """通用 HTTP 請求"""
        url = f"{self.base_url}{path}"
        headers = {'Content-Type': 'application/json'}

        data = None
        if body:
            data = json.dumps(body).encode('utf-8')

        try:
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                response_data = resp.read().decode('utf-8')
                if response_data:
                    return {'success': True, 'data': json.loads(response_data), 'status': resp.status}
                return {'success': True, 'data': {}, 'status': resp.status}
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else ''
            logger.warning(f"[FileBrowser] HTTP {e.code}: {error_body}")
            return {'success': False, 'error': f'HTTP {e.code}', 'detail': error_body[:200]}
        except urllib.error.URLError as e:
            logger.warning(f"[FileBrowser] Connection failed: {e.reason}")
            return {'success': False, 'error': f'Connection failed: {e.reason}'}
        except Exception as e:
            logger.error(f"[FileBrowser] Unexpected error: {e}")
            return {'success': False, 'error': str(e)}

    def health_check(self) -> dict:
        """檢查 FileBrowser 服務狀態"""
        result = self._request('GET', '/api/health')
        return {
            'online': result.get('success', False),
            'status': result.get('status', 0),
            'data': result.get('data'),
            'error': result.get('error'),
        }

    def get_usage_stats(self) -> dict:
        """取得儲存使用統計 (需認證，透過內部 API)"""
        result = self._request('GET', '/api/resources')
        return result


# Singleton
_filebrowser_service: Optional[FileBrowserService] = None


def get_filebrowser_service() -> FileBrowserService:
    """取得 FileBrowserService singleton"""
    global _filebrowser_service
    if _filebrowser_service is None:
        _filebrowser_service = FileBrowserService()
    return _filebrowser_service
