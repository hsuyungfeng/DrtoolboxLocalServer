"""
Notification Service — Task 11.2

Handles real-time alerts to clinic staff when high-risk patient interactions 
are detected (e.g., severe symptoms, medication reactions, or multiple escalations).

Supports:
- LINE Push notifications to on-duty staff.
- Internal alert logging for dashboard monitoring.
- Email alerting (stubbed).
"""

import logging
import os
import json
from datetime import datetime
from typing import Optional, List

import requests

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────
STAFF_NOTIFY_LINE_ID = os.getenv("STAFF_NOTIFY_LINE_ID", "") # Target staff ID
LINE_API_BASE = "https://api.line.me/v2/bot"
LINE_PUSH_URL = f"{LINE_API_BASE}/message/push"

ALERTS_LOG_DIR = os.getenv("ALERTS_LOG_DIR", "logs")
os.makedirs(ALERTS_LOG_DIR, exist_ok=True)
ALERTS_LOG_FILE = os.path.join(ALERTS_LOG_DIR, "staff_alerts.log")

class NotificationService:
    """Manages real-time staff notifications."""

    def __init__(self):
        self.token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")

    def notify_high_risk(self, patient_id: str, message: str, risk_type: str, conversation_id: str = None) -> bool:
        """
        Send a high-risk alert to staff via LINE and log it.
        
        Args:
            patient_id: The ID of the patient.
            message: The content of the high-risk message.
            risk_type: Category of risk (e.g., 'Symptom', 'Medication', 'Abuse').
            conversation_id: Reference to the conversation record.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        alert_text = (
            f"🚨 【緊急通知】偵測到高風險對話\n"
            f"⏰ 時間：{timestamp}\n"
            f"👤 病患 ID：{patient_id}\n"
            f"⚠️ 風險類型：{risk_type}\n"
            f"💬 內容：\"{message[:50]}{'...' if len(message) > 50 else ''}\"\n"
            f"🔗 請至後台處理：/dashboard/staff/patient/{patient_id}"
        )

        # 1. Log locally
        self._log_alert(patient_id, message, risk_type, conversation_id)

        # 2. Send Email Alert (Stub)
        self._send_email_alert(patient_id, risk_type, message)

        # 3. Send LINE Push to Staff
        success = True
        if STAFF_NOTIFY_LINE_ID:
            success = self._send_line_push(STAFF_NOTIFY_LINE_ID, alert_text)
            if success:
                logger.info(f"Staff notification sent to {STAFF_NOTIFY_LINE_ID} for patient {patient_id}")
        else:
            logger.warning("STAFF_NOTIFY_LINE_ID not set. Alert only logged locally.")

        return success

    def _send_line_push(self, target_id: str, text: str) -> bool:
        """Helper to send LINE push message."""
        if not self.token:
            logger.error("LINE_CHANNEL_ACCESS_TOKEN not set; cannot send staff alert.")
            return False

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
        }
        payload = {
            "to": target_id,
            "messages": [{"type": "text", "text": text}],
        }

        try:
            resp = requests.post(LINE_PUSH_URL, json=payload, headers=headers, timeout=5)
            if resp.status_code == 200:
                return True
            logger.error(f"LINE staff notify failed | status={resp.status_code} body={resp.text}")
            return False
        except Exception as e:
            logger.error(f"LINE staff notify exception | error={e}")
            return False

    def _log_alert(self, patient_id: str, message: str, risk_type: str, conversation_id: str):
        """Log the alert to a structured file for dashboard consumption."""
        try:
            with open(ALERTS_LOG_FILE, "a", encoding='utf-8') as f:
                entry = {
                    "timestamp": datetime.now().isoformat(),
                    "patient_id": patient_id,
                    "risk_type": risk_type,
                    "message": message,
                    "conversation_id": conversation_id,
                    "status": "unread"
                }
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed to log staff alert: {e}")

    def _send_email_alert(self, patient_id: str, risk_type: str, message: str) -> bool:
        """Helper to send Email alert (Stubbed)."""
        logger.info(f"Email alert stub triggered for patient {patient_id}. Risk: {risk_type}")
        # In a real implementation, this would use smtplib or an API like SendGrid
        return True

import threading
import time
import sqlite3

class RiskAlertThread:
    """Background thread checking incoming queries for critical terms."""
    def __init__(self, check_interval=10):
        self.check_interval = check_interval
        self.is_running = False
        self.last_checked_timestamp = datetime.now().isoformat()
        # Fallback path if env var is missing
        self.db_path = os.environ.get('CLINIC_DB_PATH', os.path.join(os.path.dirname(__file__), '../../../clinic.db'))
        self.critical_terms = ["流血", "劇痛", "發燒", "呼吸困難"]

    def start(self):
        if not self.is_running:
            self.is_running = True
            threading.Thread(target=self._monitor_loop, daemon=True).start()
            logger.info("🚨 Risk Alerting Background Thread started.")

    def _monitor_loop(self):
        while self.is_running:
            try:
                self._check_for_risks()
            except Exception as e:
                logger.error(f"Risk Alerting loop error: {e}")
            time.sleep(self.check_interval)

    def _check_for_risks(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        # Get new messages since last check
        rows = conn.execute(
            "SELECT id, patient_id, text, sender, timestamp FROM patient_conversations WHERE timestamp > ? AND sender = 'user' ORDER BY timestamp ASC",
            (self.last_checked_timestamp,)
        ).fetchall()
        
        for row in rows:
            self.last_checked_timestamp = max(self.last_checked_timestamp, row['timestamp'])
            text = row['text']
            if not text:
                continue
                
            for term in self.critical_terms:
                if term in text:
                    # Trigger high risk notification
                    notification_service.notify_high_risk(
                        patient_id=row['patient_id'],
                        message=text,
                        risk_type=f"Critical Term Detected: {term}",
                        conversation_id=str(row['id'])
                    )
                    
                    # Log risk status in db (escalated_flag)
                    conn.execute("UPDATE patient_conversations SET escalated_flag = 1 WHERE id = ?", (row['id'],))
                    conn.commit()
                    break
                    
        conn.close()

# Singletons
notification_service = NotificationService()
risk_alert_thread = RiskAlertThread()
