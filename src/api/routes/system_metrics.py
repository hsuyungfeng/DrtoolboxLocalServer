import sqlite3
import logging
from flask import Blueprint, jsonify, render_template
from src.db.his_connection import get_his_connection
from src.db.query_cache import QueryCache

logger = logging.getLogger(__name__)

system_metrics_bp = Blueprint('system_metrics', __name__)

@system_metrics_bp.route('/dashboard/system/', methods=['GET'])
def system_dashboard():
    """Render the system dashboard page."""
    return render_template('system_dashboard.html')

from src.services.health_monitor_service import health_monitor

@system_metrics_bp.route('/api/v1/system/metrics', methods=['GET'])
def get_metrics():
    """Get system metrics for dashboard."""
    metrics = {
        'health_check': health_monitor.get_current_health(),
        'database': {
            'pool_size': 0,
            'available_connections': 0,
            'max_connections': 0,
            'health': 'unknown'
        },
        'cache': {
            'total_items': 0,
            'total_hits': 0
        },
        'sync': {
            'last_sync_time': None,
            'last_sync_status': 'unknown',
            'pending_records': 0
        }
    }

    try:
        # 1. Database Metrics
        his = get_his_connection()
        if hasattr(his, 'pool'):
            pool = his.pool
            metrics['database']['pool_size'] = pool.created_count
            metrics['database']['available_connections'] = pool.pool.qsize()
            metrics['database']['max_connections'] = pool.config.pool_max_size
            metrics['database']['health'] = 'healthy' if pool.pool.qsize() > 0 else 'warning'
    except Exception as e:
        logger.error(f"Error getting DB metrics: {e}")
        metrics['database']['health'] = 'error'

    try:
        # 2. Cache Metrics
        cache = QueryCache()
        conn = sqlite3.connect(cache.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*), SUM(hit_count) FROM query_cache")
        row = cursor.fetchone()
        metrics['cache']['total_items'] = row[0] or 0
        metrics['cache']['total_hits'] = row[1] or 0
        
        conn.close()
    except Exception as e:
        logger.error(f"Error getting cache metrics: {e}")

    try:
        # 3. Sync Metrics (from clinic.db)
        his = get_his_connection()
        conn = sqlite3.connect(his.config.db_path)
        cursor = conn.cursor()
        
        # Check if sync_logs table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sync_logs'")
        if cursor.fetchone():
            cursor.execute("SELECT status, created_at FROM sync_logs ORDER BY created_at DESC LIMIT 1")
            last_sync = cursor.fetchone()
            if last_sync:
                metrics['sync']['last_sync_status'] = last_sync[0]
                metrics['sync']['last_sync_time'] = last_sync[1]
            
            cursor.execute("SELECT COUNT(*) FROM sync_logs WHERE status='pending'")
            pending = cursor.fetchone()
            metrics['sync']['pending_records'] = pending[0] if pending else 0
        else:
            metrics['sync']['last_sync_status'] = 'not_configured'
            
        conn.close()
    except Exception as e:
        logger.error(f"Error getting sync metrics: {e}")

    return jsonify(metrics)
