"""
CRM Analyzer Service - CRM 分析管線服務

提供診所 CRM 數據分析功能，包括：
- 患者回診追蹤分析
- 健康趨勢分析
- 預約提醒名單
- 週度綜合報告

主要功能：
- analyze_patient_retention() - 分析 6 個月未回診患者
- analyze_health_trends() - 健康趨勢分析
- analyze_appointments() - 未來 3 天預約提醒
- analyze_weekly_summary() - 週度綜合報告
"""

import os
import sys
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

logger = logging.getLogger(__name__)

DB_PATH = os.environ.get('CLINIC_DB_PATH', os.path.join(os.path.dirname(__file__), '../../clinic.db'))


def _get_db_connection():
    """取得資料庫連線"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_crm_reports_table():
    """確保 crm_reports 資料表存在"""
    conn = _get_db_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS crm_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT,
                data_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_auto INTEGER DEFAULT 0
            )
        """)
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to create crm_reports table: {e}")
    finally:
        conn.close()


class CRMAnalyzer:
    """CRM 分析器"""

    def __init__(self):
        self.db_path = DB_PATH
        _ensure_crm_reports_table()

    def analyze_patient_retention(self, months_threshold: int = 6) -> Dict[str, Any]:
        """分析患者回診追蹤 — 找出超過 N 個月未回診的患者"""
        conn = _get_db_connection()
        try:
            cutoff_date = (datetime.now() - timedelta(days=months_threshold * 30)).strftime('%Y-%m-%d')
            
            rows = conn.execute("""
                SELECT p.patient_id, p.name, p.phone, p.email,
                       MAX(a.appointment_date) as last_visit
                FROM patients p
                LEFT JOIN appointments a ON p.patient_id = a.patient_id
                GROUP BY p.patient_id
                HAVING last_visit < ? OR last_visit IS NULL
                ORDER BY last_visit ASC
                LIMIT 50
            """, (cutoff_date,)).fetchall()

            patients = [dict(row) for row in rows]
            
            summary = (
                f"發現 {len(patients)} 位超過 {months_threshold} 個月未回診的患者。\n"
                f"建議：主動聯繫追蹤，了解健康狀況並安排回診。"
            )

            report = {
                'category': 'patient_retention',
                'title': f'患者回診追蹤分析 — {datetime.now().strftime("%Y-%m-%d")}',
                'summary': summary,
                'data': {
                    'threshold_months': months_threshold,
                    'cutoff_date': cutoff_date,
                    'at_risk_count': len(patients),
                    'patients': patients,
                }
            }

            self._save_report(report, is_auto=True)
            return {'success': True, 'data': report}
        except Exception as e:
            logger.error(f"Patient retention analysis failed: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()

    def analyze_health_trends(self) -> Dict[str, Any]:
        """分析健康趨勢 — 近期看診模式統計"""
        conn = _get_db_connection()
        try:
            # 取得近 30 天預約統計
            thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
            visit_count = conn.execute(
                "SELECT COUNT(*) as cnt FROM appointments WHERE appointment_date >= ?",
                (thirty_days_ago,)
            ).fetchone()['cnt']

            # 取得每日看診量
            daily_visits = conn.execute("""
                SELECT appointment_date as date, COUNT(*) as count
                FROM appointments
                WHERE appointment_date >= ?
                GROUP BY appointment_date
                ORDER BY appointment_date
            """, (thirty_days_ago,)).fetchall()

            summary = (
                f"近 30 天共有 {visit_count} 筆就診記錄。\n"
                f"日均就診量：{visit_count / 30:.1f} 人次。"
            )

            report = {
                'category': 'health_trends',
                'title': f'健康趨勢分析 — {datetime.now().strftime("%Y-%m-%d")}',
                'summary': summary,
                'data': {
                    'period_days': 30,
                    'total_visits': visit_count,
                    'daily_average': round(visit_count / 30, 1),
                    'daily_visits': [dict(row) for row in daily_visits],
                }
            }

            self._save_report(report, is_auto=True)
            return {'success': True, 'data': report}
        except Exception as e:
            logger.error(f"Health trends analysis failed: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()

    def analyze_appointments(self, days_ahead: int = 3) -> Dict[str, Any]:
        """分析未來 N 天預約 — 提醒名單"""
        conn = _get_db_connection()
        try:
            start = datetime.now().strftime('%Y-%m-%d')
            end = (datetime.now() + timedelta(days=days_ahead)).strftime('%Y-%m-%d')

            rows = conn.execute("""
                SELECT a.appointment_id, a.appointment_date,
                       p.patient_id, p.name as patient_name, p.phone, p.email
                FROM appointments a
                JOIN patients p ON a.patient_id = p.patient_id
                WHERE a.appointment_date BETWEEN ? AND ?
                ORDER BY a.appointment_date
                LIMIT 50
            """, (start, end)).fetchall()

            appointments = [dict(row) for row in rows]

            summary = (
                f"未來 {days_ahead} 天內有 {len(appointments)} 個預約。\n"
                f"建議：提前發送提醒給患者。"
            )

            report = {
                'category': 'appointment_reminders',
                'title': f'預約提醒名單 — {datetime.now().strftime("%Y-%m-%d")}',
                'summary': summary,
                'data': {
                    'days_ahead': days_ahead,
                    'from_date': start,
                    'to_date': end,
                    'count': len(appointments),
                    'appointments': appointments,
                }
            }

            self._save_report(report, is_auto=True)
            return {'success': True, 'data': report}
        except Exception as e:
            logger.error(f"Appointment analysis failed: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()

    def analyze_weekly_summary(self) -> Dict[str, Any]:
        """週度綜合報告"""
        conn = _get_db_connection()
        try:
            week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

            # 本週就診量
            visit_count = conn.execute(
                "SELECT COUNT(*) as cnt FROM appointments WHERE appointment_date >= ?",
                (week_ago,)
            ).fetchone()['cnt']

            # 患者總數
            total_patients = conn.execute(
                "SELECT COUNT(*) as cnt FROM patients"
            ).fetchone()['cnt']

            # 新患者 (近 7 天建立)
            new_patients = conn.execute(
                "SELECT COUNT(*) as cnt FROM patients WHERE created_at >= ?",
                (week_ago,)
            ).fetchone()['cnt']

            summary = (
                f"週度綜合報告 ({week_ago} ~ {datetime.now().strftime('%Y-%m-%d')})：\n"
                f"本週就診量：{visit_count} 人次\n"
                f"活躍患者總數：{total_patients}\n"
                f"本週新增患者：{new_patients}\n"
                f"建議：持續監控就診趨勢，優化排班。"
            )

            report = {
                'category': 'weekly_summary',
                'title': f'週度綜合報告 — {datetime.now().strftime("%Y-%m-%d")}',
                'summary': summary,
                'data': {
                    'from_date': week_ago,
                    'to_date': datetime.now().strftime('%Y-%m-%d'),
                    'weekly_visits': visit_count,
                    'total_active_patients': total_patients,
                    'new_patients_this_week': new_patients,
                }
            }

            self._save_report(report, is_auto=True)
            return {'success': True, 'data': report}
        except Exception as e:
            logger.error(f"Weekly summary analysis failed: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()

    def _save_report(self, report: Dict[str, Any], is_auto: bool = False):
        """儲存報告到資料庫"""
        import json
        conn = _get_db_connection()
        try:
            conn.execute(
                "INSERT INTO crm_reports (category, title, summary, data_json, is_auto) VALUES (?, ?, ?, ?, ?)",
                (
                    report['category'],
                    report['title'],
                    report['summary'],
                    json.dumps(report['data'], ensure_ascii=False),
                    1 if is_auto else 0,
                )
            )
            conn.commit()
            logger.info(f"[CRM] Report saved: {report['title']}")
        except Exception as e:
            logger.error(f"Failed to save CRM report: {e}")
        finally:
            conn.close()

    def get_reports(self, category: str = None, limit: int = 20) -> List[Dict]:
        """取得歷史報告"""
        conn = _get_db_connection()
        try:
            if category:
                rows = conn.execute(
                    "SELECT * FROM crm_reports WHERE category = ? ORDER BY created_at DESC LIMIT ?",
                    (category, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM crm_reports ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_latest_report(self, category: str) -> Optional[Dict]:
        """取得最新一份特定類別的報告"""
        conn = _get_db_connection()
        try:
            row = conn.execute(
                "SELECT * FROM crm_reports WHERE category = ? ORDER BY created_at DESC LIMIT 1",
                (category,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


# Singleton
_crm_analyzer: Optional[CRMAnalyzer] = None


def get_crm_analyzer() -> CRMAnalyzer:
    """取得 CRMAnalyzer singleton"""
    global _crm_analyzer
    if _crm_analyzer is None:
        _crm_analyzer = CRMAnalyzer()
    return _crm_analyzer
