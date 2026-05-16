import os
import json
import logging
from datetime import datetime, timezone
import threading
from config.settings import LOG_DIR

logger = logging.getLogger(__name__)

class JSONLLogger:
    def __init__(self):
        os.makedirs(LOG_DIR, exist_ok=True)
        self.lock = threading.Lock()
        
    def _get_daily_file(self):
        date_str = datetime.now().strftime("%Y-%m-%d")
        return os.path.join(LOG_DIR, f"interactions_{date_str}.jsonl")
        
    def log_interaction(self, user_id, prompt, response, route_used, context_nodes=None):
        """Logs the interaction safely across threads into a daily JSONL file."""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "messages": [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": response}
            ],
            "metadata": {
                "route_used": route_used,
                "context_nodes": context_nodes or []
            }
        }
        
        filepath = self._get_daily_file()
        try:
            with self.lock:
                with open(filepath, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"Failed to log interaction: {e}")

logger_service = JSONLLogger()
