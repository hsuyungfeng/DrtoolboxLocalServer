"""
AstrBot Service - AstrBot 聊天機器人橋接服務

提供與 AstrBot 容器的 HTTP API 通訊，包括：
- 健康檢查 (health check)
- 取得已啟動平台列表 (LINE/Telegram 等)
- 發送 IM 訊息
- 取得聊天會話列表
- 程式化聊天

主要功能：
- health_check() - 檢查 AstrBot 服務狀態
- get_bots() - 取得已啟動平台列表
- send_message(platform, target, content) - 發送訊息
- get_sessions() - 取得活躍會話
- chat(session_id, message) - 進行聊天
"""

import os
import sys
import json
import logging
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

logger = logging.getLogger(__name__)


class AstrBotService:
    """AstrBot API 橋接服務"""

    def __init__(self):
        self.base_url = os.getenv('ASTRBOT_URL', 'http://localhost:6185')
        self.api_key = os.getenv('ASTRBOT_API_KEY', '')
        self.timeout = 5

    def _request(self, method: str, path: str, body: dict = None, headers_extra: dict = None) -> Dict[str, Any]:
        """通用 HTTP 請求"""
        url = f"{self.base_url}{path}"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}',
        }
        if headers_extra:
            headers.update(headers_extra)

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
            logger.warning(f"[AstrBot] HTTP {e.code} for {method} {path}: {error_body}")
            return {'success': False, 'error': f'HTTP {e.code}', 'detail': error_body[:200]}
        except urllib.error.URLError as e:
            logger.warning(f"[AstrBot] Connection failed: {e.reason}")
            return {'success': False, 'error': f'Connection failed: {e.reason}'}
        except Exception as e:
            logger.error(f"[AstrBot] Unexpected error: {e}")
            return {'success': False, 'error': str(e)}

    def health_check(self) -> dict:
        """檢查 AstrBot 服務是否在線
        回傳: {"online": bool, "uptime": str, "version": str}
        """
        result = self._request('GET', '/api/stat/start-time')
        if result.get('success'):
            return {
                'online': True,
                'data': result.get('data', {}),
                'version': 'detected',
            }
        return {'online': False, 'error': result.get('error', 'Unknown')}

    def get_bots(self) -> dict:
        """取得已啟動的聊天機器人平台列表"""
        return self._request('GET', '/api/v1/im/bots')

    def send_message(self, platform: str, target: str, content: str) -> dict:
        """發送 IM 訊息至指定平台與目標
        Args:
            platform: 平台名稱 (ex: 'qq_official', 'wechat_official')
            target: 目標 ID (ex: 使用者 ID, 群組 ID)
            content: 訊息內容
        """
        body = {
            'platform': platform,
            'target': target,
            'message': content,
        }
        return self._request('POST', '/api/v1/im/message', body=body)

    def get_sessions(self) -> dict:
        """取得當前活躍的聊天會話列表"""
        result = self._request('GET', '/api/v1/chat/sessions')
        return result

    def chat(self, session_id: str, message: str) -> dict:
        """發送聊天訊息
        Args:
            session_id: 會話 ID
            message: 訊息內容
        """
        body = {
            'session_id': session_id,
            'message': message,
        }
        return self._request('POST', '/api/v1/chat', body=body)


# Singleton
_astrbot_service: Optional[AstrBotService] = None


def get_astrbot_service() -> AstrBotService:
    """取得 AstrBotService singleton"""
    global _astrbot_service
    if _astrbot_service is None:
        _astrbot_service = AstrBotService()
    return _astrbot_service
