"""
System Setup API - 系統設定 API

提供集中式的系統設定讀寫端點，管理 .env 環境變數與 config/*.json 設定檔

Endpoints:
- GET  /api/v1/setup/config - 讀取所有系統設定 (env + config files)
- POST /api/v1/setup/config - 寫入設定 (env 變數或 config file)
- GET  /api/v1/setup/services - 取得外部服務連線狀態
- POST /api/v1/setup/services/restart - 重啟指定服務
- GET  /api/v1/setup/export - 匯出完整設定備份 (JSON)
- POST /api/v1/setup/import - 匯入設定備份 (JSON)
- GET  /api/v1/setup/logs - 取得設定變更歷史記錄
"""

import os
import sys
import sqlite3
import json
import logging
import re
import subprocess
from datetime import datetime
from flask import Blueprint, jsonify, request, render_template

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

logger = logging.getLogger(__name__)

setup_bp = Blueprint('setup', __name__)

DB_PATH = os.environ.get('CLINIC_DB_PATH', os.path.join(os.path.dirname(__file__), '../../../clinic.db'))

# Config file paths (relative to project root)
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '../../..')
ENV_PATH = os.path.join(PROJECT_ROOT, '.env')
CONFIG_DIR = os.path.join(PROJECT_ROOT, 'config')

CONFIG_FILES = {
    'llama': 'llama_config.json',
    'llama_cuda': 'llama_cuda_config.json',
    'memory': 'memory_config.json',
    'ingest': 'ingest_config.json',
}

# 敏感欄位清單（回傳時遮罩）
SENSITIVE_KEYS = [
    'DEEPSEEK_API_KEY', 'LINE_CHANNEL_SECRET', 'LINE_CHANNEL_ACCESS_TOKEN',
    'api_key', 'secret', 'password', 'token',
    'DRTOOLBOX_CHAT_API_KEY', 'FB_PAGE_ACCESS_TOKEN', 'FB_VERIFY_TOKEN',
    'WHATSAPP_API_KEY', 'INSTAGRAM_API_KEY',
]


def _get_db_connection():
    """取得資料庫連線"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_setup_logs_table():
    """確保 setup_logs 資料表存在"""
    conn = _get_db_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS setup_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                section TEXT NOT NULL,
                key TEXT,
                old_value TEXT,
                new_value TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to create setup_logs table: {e}")
    finally:
        conn.close()


def _log_setup_change(action: str, section: str, key: str = None, old_value: str = None, new_value: str = None):
    """記錄設定變更到 setup_logs"""
    conn = _get_db_connection()
    try:
        conn.execute(
            "INSERT INTO setup_logs (action, section, key, old_value, new_value) VALUES (?, ?, ?, ?, ?)",
            (action, section, key, old_value, new_value)
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to log setup change: {e}")
    finally:
        conn.close()


def _mask_sensitive_value(key: str, value: str) -> str:
    """遮罩敏感值（只顯示前 4 後 4 字元）"""
    if not value or not isinstance(value, str):
        return value
    for sensitive in SENSITIVE_KEYS:
        if sensitive.lower() in key.lower():
            if len(value) > 8:
                return value[:4] + '*' * (len(value) - 8) + value[-4:]
            elif len(value) > 2:
                return value[:2] + '*' * (len(value) - 2)
            return '***'
    return value


def _read_env_file() -> dict:
    """讀取 .env 檔案為 dict"""
    env_vars = {}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    env_vars[key] = value
    return env_vars


def _write_env_file(env_vars: dict):
    """寫入 .env 檔案"""
    with open(ENV_PATH, 'w', encoding='utf-8') as f:
        for key, value in env_vars.items():
            f.write(f'{key}={value}\n')


def _read_config_file(name: str) -> dict:
    """讀取 config JSON 檔案"""
    filename = CONFIG_FILES.get(name)
    if not filename:
        return {}
    filepath = os.path.join(CONFIG_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def _write_config_file(name: str, data: dict):
    """寫入 config JSON 檔案"""
    filename = CONFIG_FILES.get(name)
    if not filename:
        raise ValueError(f"Unknown config file: {name}")
    filepath = os.path.join(CONFIG_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ============================================================
# Config Endpoints
# ============================================================

@setup_bp.route('/api/v1/setup/config', methods=['GET'])
def get_config():
    """讀取所有系統設定"""
    try:
        result = {'env': {}, 'configs': {}}

        # 讀取 .env
        env_vars = _read_env_file()
        for key, value in env_vars.items():
            result['env'][key] = _mask_sensitive_value(key, value)

        # 讀取各 config 檔案
        for config_name in CONFIG_FILES:
            result['configs'][config_name] = _read_config_file(config_name)

        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.error(f"Error reading config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@setup_bp.route('/api/v1/setup/config', methods=['POST'])
def set_config():
    """寫入系統設定
    Body: {
        "section": "env" | "llama" | "llama_cuda" | "memory" | "ingest",
        "key": "設定鍵名",
        "value": "新值"
    }
    或針對 config JSON 物件:
    {
        "section": "llama",
        "data": { ... }    // 完整取代 config file 內容
    }
    """
    try:
        body = request.get_json()
        if not body:
            return jsonify({'success': False, 'error': 'Missing request body'}), 400

        section = body.get('section')
        key = body.get('key')
        value = body.get('value')
        data = body.get('data')

        if not section:
            return jsonify({'success': False, 'error': 'Missing "section" field'}), 400

        # 寫入 .env
        if section == 'env':
            if not key or value is None:
                return jsonify({'success': False, 'error': 'Missing "key" or "value" for env section'}), 400

            env_vars = _read_env_file()
            old_value = env_vars.get(key)
            env_vars[key] = str(value)
            _write_env_file(env_vars)
            _log_setup_change('update', 'env', key, old_value, str(value))
            logger.info(f"[Setup] env.{key} updated")
            return jsonify({'success': True, 'message': f'env.{key} updated', 'data': {'key': key, 'value': _mask_sensitive_value(key, str(value))}})

        # 寫入 config JSON 檔案（整檔覆蓋）
        elif section in CONFIG_FILES:
            if data is not None:
                old_data = _read_config_file(section)
                _write_config_file(section, data)
                _log_setup_change('update', f'config.{section}', None, json.dumps(old_data, ensure_ascii=False)[:500], json.dumps(data, ensure_ascii=False)[:500])
                logger.info(f"[Setup] config.{section}.json updated (full replace)")
                return jsonify({'success': True, 'message': f'config.{section}.json updated'})
            elif key and value is not None:
                # 部分更新：更新 JSON 中的特定 key
                config_data = _read_config_file(section)
                old_val = config_data.get(key)
                config_data[key] = value
                _write_config_file(section, config_data)
                _log_setup_change('update', f'config.{section}', key, str(old_val), str(value))
                logger.info(f"[Setup] config.{section}.json[{key}] updated")
                return jsonify({'success': True, 'message': f'config.{section}.{key} updated'})
            else:
                return jsonify({'success': False, 'error': 'Provide "data" (full replace) or "key"+"value" (partial update)'}), 400
        else:
            return jsonify({'success': False, 'error': f'Unknown section: {section}'}), 400

    except Exception as e:
        logger.error(f"Error writing config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# Services Endpoints
# ============================================================

@setup_bp.route('/api/v1/setup/services', methods=['GET'])
def get_services_status():
    """取得外部服務連線狀態"""
    services = {
        'filebrowser': {'name': 'FileBrowser 檔案管理', 'online': False, 'url': os.getenv('FILEBROWSER_URL', 'http://localhost:8081'), 'health_path': '/api/health', 'error': None},
        'hermes_agent': {'name': 'Hermes Agent', 'online': False, 'url': os.getenv('HERMES_AGENT_URL', 'http://127.0.0.1:8642'), 'health_path': '/health', 'error': None},
    }

    import urllib.request
    for svc_key, svc in services.items():
        try:
            health_url = f"{svc['url']}{svc.get('health_path', '/health')}"
            req = urllib.request.Request(health_url)
            with urllib.request.urlopen(req, timeout=3) as resp:
                svc['online'] = resp.status == 200
        except Exception as e:
            svc['error'] = str(e.__class__.__name__)

    return jsonify({'success': True, 'data': services})


@setup_bp.route('/api/v1/setup/services/restart', methods=['POST'])
def restart_service():
    """重啟指定服務 (透過 docker compose)"""
    try:
        body = request.get_json()
        if not body:
            return jsonify({'success': False, 'error': 'Missing request body'}), 400

        service_name = body.get('service')
        valid_services = ['astrbot', 'filebrowser', 'drtoolbox', 'nginx', 'hermes-agent']

        if service_name not in valid_services:
            return jsonify({'success': False, 'error': f'Invalid service. Valid: {valid_services}'}), 400

        compose_file = os.path.join(PROJECT_ROOT, 'docker-compose.yml')
        if not os.path.exists(compose_file):
            return jsonify({'success': False, 'error': 'docker-compose.yml not found'}), 500

        result = subprocess.run(
            ['docker', 'compose', '-f', compose_file, 'restart', service_name],
            capture_output=True, text=True, timeout=30
        )

        _log_setup_change('restart', 'services', service_name, None, 'success' if result.returncode == 0 else result.stderr[:200])
        logger.info(f"[Setup] Service restart: {service_name} -> {'OK' if result.returncode == 0 else 'FAIL'}")

        return jsonify({
            'success': result.returncode == 0,
            'message': f'Service {service_name} restart {"succeeded" if result.returncode == 0 else "failed"}',
            'data': {'stdout': result.stdout, 'stderr': result.stderr}
        })
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'Restart timed out'}), 504
    except Exception as e:
        logger.error(f"Error restarting service: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# Export / Import Endpoints
# ============================================================

@setup_bp.route('/api/v1/setup/export', methods=['GET'])
def export_config():
    """匯出完整設定備份 (JSON)"""
    try:
        export_data = {
            'exported_at': datetime.now().isoformat(),
            'env': _read_env_file(),
            'configs': {}
        }
        for config_name in CONFIG_FILES:
            export_data['configs'][config_name] = _read_config_file(config_name)

        # 遮罩敏感值後回傳
        for key in list(export_data['env'].keys()):
            export_data['env'][key] = _mask_sensitive_value(key, export_data['env'][key])

        _log_setup_change('export', 'backup', None, None, None)
        return jsonify({'success': True, 'data': export_data})
    except Exception as e:
        logger.error(f"Error exporting config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@setup_bp.route('/api/v1/setup/import', methods=['POST'])
def import_config():
    """匯入設定備份 (JSON body)"""
    try:
        body = request.get_json()
        if not body:
            return jsonify({'success': False, 'error': 'Missing request body'}), 400

        import_count = 0

        # 寫入 env
        if 'env' in body and isinstance(body['env'], dict):
            env_vars = _read_env_file()
            for key, value in body['env'].items():
                if '*' not in str(value):  # 跳過已遮罩的值
                    env_vars[key] = str(value)
                    import_count += 1
            _write_env_file(env_vars)

        # 寫入 config files
        if 'configs' in body and isinstance(body['configs'], dict):
            for config_name, config_data in body['configs'].items():
                if config_name in CONFIG_FILES:
                    _write_config_file(config_name, config_data)
                    import_count += 1

        _log_setup_change('import', 'backup', None, None, f'{import_count} items imported')
        logger.info(f"[Setup] Config import: {import_count} items")

        return jsonify({'success': True, 'message': f'{import_count} items imported', 'data': {'imported_count': import_count}})
    except Exception as e:
        logger.error(f"Error importing config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# Setup Logs Endpoint
# ============================================================

@setup_bp.route('/api/v1/setup/logs', methods=['GET'])
def get_setup_logs():
    """取得設定變更歷史記錄（最近 20 筆）"""
    try:
        _ensure_setup_logs_table()
        conn = _get_db_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM setup_logs ORDER BY timestamp DESC LIMIT 20"
            ).fetchall()
            logs = [dict(row) for row in rows]
            return jsonify({'success': True, 'data': logs})
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Error reading setup logs: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# Setup Dashboard Page
# ============================================================

@setup_bp.route('/dashboard/setup/', methods=['GET'])
def setup_dashboard():
    """系統設定儀表板頁面"""
    return render_template('setup.html')
