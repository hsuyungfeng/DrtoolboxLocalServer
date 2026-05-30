import os
import time
import threading
import requests
import logging
import psutil
import json
from datetime import datetime
from config.settings import DATA_DIR

logger = logging.getLogger(__name__)

class HealthMonitorService:
    def __init__(self, check_interval=60):
        self.check_interval = check_interval
        self.is_running = False
        self.health_history = []
        self.max_history = 100
        self.status_file = os.path.join(DATA_DIR, 'system_health.json')
        
        # Service URLs
        self.backend_url = "http://127.0.0.1:5000/health"
        self.llm_url = "http://127.0.0.1:8080/health"

    def start(self):
        if not self.is_running:
            self.is_running = True
            threading.Thread(target=self._monitor_loop, daemon=True).start()
            logger.info("🚀 Hermes Health Monitor started.")

    def _monitor_loop(self):
        while self.is_running:
            try:
                health_data = self.perform_check()
                self._save_status(health_data)
                self._handle_auto_correction(health_data)
            except Exception as e:
                logger.error(f"Health monitor loop error: {e}")
            
            time.sleep(self.check_interval)

    def perform_check(self):
        """Checks the pulse of all critical system components."""
        stats = {
            "timestamp": datetime.now().isoformat(),
            "services": {
                "flask_backend": self._check_url(self.backend_url),
                "llm_engine": self._check_url(self.llm_url),
            },
            "resources": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent
            },
            "status": "healthy"
        }

        # Determine overall status
        if stats["services"]["flask_backend"] != "online" or stats["services"]["llm_engine"] != "online":
            stats["status"] = "critical"
        elif stats["resources"]["memory_percent"] > 90:
            stats["status"] = "warning"

        return stats

    def _check_url(self, url):
        try:
            res = requests.get(url, timeout=5)
            return "online" if res.status_code == 200 else "offline"
        except:
            return "offline"

    def _save_status(self, data):
        self.health_history.append(data)
        if len(self.health_history) > self.max_history:
            self.health_history.pop(0)
            
        with open(self.status_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def _handle_auto_correction(self, data):
        """Self-healing logic."""
        if data["services"]["llm_engine"] == "offline":
            logger.warning("🚨 LLM Engine offline! Attempting to restart container...")
            os.system("docker start llama-qwen")
            
        if data["resources"]["memory_percent"] > 95:
            logger.error("🛑 System low on memory! Alerting administrator...")
            # Future: Send LINE notification to admin

    def get_current_health(self):
        if os.path.exists(self.status_file):
            with open(self.status_file, 'r') as f:
                return json.load(f)
        return {"status": "unknown"}

health_monitor = HealthMonitorService()
