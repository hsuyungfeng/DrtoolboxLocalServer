"""
CRM Reports API - CRM 分析報告 API

提供 CRM 分析報告的查詢與手動觸發

Endpoints:
- GET  /api/v1/crm/reports       - 取得所有 CRM 報告列表
- GET  /api/v1/crm/reports/{id}  - 取得指定報告詳細內容
- POST /api/v1/crm/analyze       - 手動觸發分析
- GET  /api/v1/crm/status        - CRM 分析狀態 (已產出的報告類別)
- GET  /dashboard/crm/           - CRM 報告儀表板頁面
"""

import os
import sys
import logging
from flask import Blueprint, jsonify, request, render_template

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.services.crm_analyzer import get_crm_analyzer

logger = logging.getLogger(__name__)

crm_reports_bp = Blueprint('crm_reports', __name__)

crm_analyzer = get_crm_analyzer()

ANALYSIS_TYPES = {
    'patient_retention': '患者回診追蹤',
    'health_trends': '健康趨勢',
    'appointment_reminders': '預約提醒',
    'weekly_summary': '週度綜合報告',
}


@crm_reports_bp.route('/api/v1/crm/reports', methods=['GET'])
def list_reports():
    """取得 CRM 報告列表"""
    try:
        category = request.args.get('category')
        limit = int(request.args.get('limit', 20))
        reports = crm_analyzer.get_reports(category=category, limit=limit)
        return jsonify({'success': True, 'data': reports})
    except Exception as e:
        logger.error(f"Error listing CRM reports: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_reports_bp.route('/api/v1/crm/reports/<int:report_id>', methods=['GET'])
def get_report(report_id: int):
    """取得指定報告詳細內容"""
    try:
        reports = crm_analyzer.get_reports(limit=100)
        report = next((r for r in reports if r.get('id') == report_id), None)
        if report:
            return jsonify({'success': True, 'data': report})
        return jsonify({'success': False, 'error': 'Report not found'}), 404
    except Exception as e:
        logger.error(f"Error getting CRM report {report_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_reports_bp.route('/api/v1/crm/analyze', methods=['POST'])
def trigger_analysis():
    """手動觸發 CRM 分析
    Body: { "type": "patient_retention" | "health_trends" | "appointment_reminders" | "weekly_summary" }
    """
    try:
        body = request.get_json()
        if not body:
            return jsonify({'success': False, 'error': 'Missing request body'}), 400

        analysis_type = body.get('type')
        if analysis_type not in ANALYSIS_TYPES:
            valid = ', '.join(ANALYSIS_TYPES.keys())
            return jsonify({'success': False, 'error': f'Invalid type. Valid: {valid}'}), 400

        # 執行對應分析
        if analysis_type == 'patient_retention':
            result = crm_analyzer.analyze_patient_retention()
        elif analysis_type == 'health_trends':
            result = crm_analyzer.analyze_health_trends()
        elif analysis_type == 'appointment_reminders':
            result = crm_analyzer.analyze_appointments()
        elif analysis_type == 'weekly_summary':
            result = crm_analyzer.analyze_weekly_summary()
        else:
            return jsonify({'success': False, 'error': f'Unknown type: {analysis_type}'}), 400

        if result.get('success'):
            logger.info(f"[CRM] Manual analysis triggered: {analysis_type}")
            return jsonify({'success': True, 'data': result['data'], 'message': f'{ANALYSIS_TYPES[analysis_type]} 分析完成'})
        return jsonify({'success': False, 'error': result.get('error', 'Analysis failed')}), 500
    except Exception as e:
        logger.error(f"Error triggering CRM analysis: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_reports_bp.route('/api/v1/crm/status', methods=['GET'])
def crm_status():
    """CRM 分析狀態 — 各類別最新報告摘要"""
    try:
        status = {}
        for key, label in ANALYSIS_TYPES.items():
            latest = crm_analyzer.get_latest_report(key)
            status[key] = {
                'label': label,
                'has_report': latest is not None,
                'latest_time': latest.get('created_at') if latest else None,
                'latest_summary': latest.get('summary', '')[:100] if latest else None,
            }
        return jsonify({'success': True, 'data': status})
    except Exception as e:
        logger.error(f"Error getting CRM status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_reports_bp.route('/dashboard/crm/', methods=['GET'])
def crm_dashboard():
    """CRM 報告儀表板頁面"""
    return render_template('crm_reports.html')
