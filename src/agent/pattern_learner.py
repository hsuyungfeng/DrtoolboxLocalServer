"""
Pattern Learner

Analyzes staff conversations to identify frequently asked questions or repetitive tasks.
Generates 'Candidate Skills' that can be approved to become Auto-Skills.
Enhanced with semantic pattern detection and SQLite storage.
"""

import logging
import sqlite3
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class PatternLearner:
    """Monitors chat history and suggests Auto-Skills with semantic pattern detection."""
    
    def __init__(self, db_path: str = "data/local_db/clinic.db", 
                 pattern_threshold: int = 3, 
                 similarity_threshold: float = 0.8):
        self.db_path = db_path
        self.history_cache = []
        self.pattern_threshold = pattern_threshold  # 3 occurrences in 7 days
        self.similarity_threshold = similarity_threshold
        
    def _get_conn(self):
        return sqlite3.connect(self.db_path)
    
    def _get_db_path(self):
        """Get absolute path for database."""
        import os
        if os.path.isabs(self.db_path):
            return self.db_path
        # Try relative to project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(project_root, self.db_path)
        
    def log_query(self, query: str, user: str = "unknown"):
        """Log a user query for pattern analysis."""
        self.history_cache.append(query)
        
        # Also store in database for persistence
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Check for existing similar pattern (simple text match for now)
            cursor.execute(
                "SELECT pattern_id, frequency FROM patterns WHERE pattern_text = ?",
                (query.lower().strip(),)
            )
            existing = cursor.fetchone()
            
            if existing:
                # Update frequency
                cursor.execute(
                    "UPDATE patterns SET frequency = frequency + 1, updated_at = ? WHERE pattern_id = ?",
                    (datetime.now().isoformat(), existing[0])
                )
            else:
                # Insert new pattern
                pattern_id = f"pat_{uuid.uuid4().hex[:8]}"
                cursor.execute(
                    """INSERT INTO patterns (pattern_id, pattern_text, category, frequency, confidence, status)
                       VALUES (?, ?, ?, 1, ?, 'pending')""",
                    (pattern_id, query.lower().strip(), "general", 0.5)
                )
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to log query to database: {e}")
            
        logger.info(f"Logged query for pattern analysis: {query}")
    
    def _categorize_pattern(self, pattern_text: str) -> str:
        """Categorize a pattern based on keywords."""
        text = pattern_text.lower()
        
        if any(w in text for w in ["patient", "病患", "病人", "看診", "掛號"]):
            return "patient_query"
        elif any(w in text for w in ["schedule", "排班", "班表", "預約", "門診"]):
            return "clinic_operation"
        elif any(w in text for w in ["medicine", "藥物", "處方", "用藥", " dosage"]):
            return "medical_info"
        elif any(w in text for w in ["task", "工作", "任務", "完成", "處理"]):
            return "staff_task"
        else:
            return "general"
    
    def _calculate_confidence(self, frequency: int, category: str) -> float:
        """Calculate confidence score based on frequency and category."""
        base_confidence = min(frequency / 10.0, 1.0)  # Max out at 10 occurrences
        
        # Boost confidence for certain categories
        category_boost = {
            "patient_query": 0.1,
            "medical_info": 0.15,
            "clinic_operation": 0.1,
            "staff_task": 0.05,
            "general": 0.0
        }
        
        return min(base_confidence + category_boost.get(category, 0), 1.0)
    
    def detect_patterns(self) -> List[Dict[str, Any]]:
        """
        Analyze recent history and detect patterns in the database.
        Returns patterns that meet the threshold criteria.
        """
        try:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get patterns that meet frequency threshold and are pending
            cursor.execute(
                """SELECT * FROM patterns 
                   WHERE frequency >= ? AND status = 'pending'
                   ORDER BY frequency DESC, updated_at DESC""",
                (self.pattern_threshold,)
            )
            patterns = cursor.fetchall()
            
            conn.close()
            
            result = []
            for p in patterns:
                pattern_dict = dict(p)
                # Recalculate confidence
                pattern_dict['confidence'] = self._calculate_confidence(
                    p['frequency'], p['category']
                )
                # Auto-categorize if still general
                if p['category'] == 'general':
                    pattern_dict['category'] = self._categorize_pattern(p['pattern_text'])
                result.append(pattern_dict)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to detect patterns: {e}")
            return []
    
    def extract_candidates(self) -> List[Dict[str, Any]]:
        """
        Legacy method - returns candidate skills from detected patterns.
        Now uses database-backed detection.
        """
        patterns = self.detect_patterns()
        
        candidates = []
        for p in patterns:
            candidates.append({
                "pattern_id": p['pattern_id'],
                "pattern": p['pattern_text'],
                "frequency": p['frequency'],
                "category": p.get('category', 'general'),
                "confidence": p.get('confidence', 0.5),
                "suggested_name": f"auto_skill_{p['pattern_id']}",
                "description": f"Auto-generated skill for pattern: {p['pattern_text']}"
            })
            
        return candidates
    
    def approve_pattern(self, pattern_id: str) -> Optional[Dict[str, Any]]:
        """Approve a pattern and mark it as approved in database."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cursor.execute(
                "UPDATE patterns SET status = 'approved', updated_at = ? WHERE pattern_id = ?",
                (datetime.now().isoformat(), pattern_id)
            )
            conn.commit()
            
            cursor.execute("SELECT * FROM patterns WHERE pattern_id = ?", (pattern_id,))
            pattern = cursor.fetchone()
            conn.close()
            
            return dict(pattern) if pattern else None
            
        except Exception as e:
            logger.error(f"Failed to approve pattern: {e}")
            return None
    
    def reject_pattern(self, pattern_id: str) -> bool:
        """Reject a pattern and mark it as rejected in database."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cursor.execute(
                "UPDATE patterns SET status = 'rejected', updated_at = ? WHERE pattern_id = ?",
                (datetime.now().isoformat(), pattern_id)
            )
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Failed to reject pattern: {e}")
            return False
    
    def get_pattern_stats(self) -> Dict[str, Any]:
        """Get pattern statistics."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM patterns")
            total = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM patterns WHERE status = 'pending'")
            pending = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM patterns WHERE status = 'approved'")
            approved = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM patterns WHERE status = 'rejected'")
            rejected = cursor.fetchone()[0]
            
            cursor.execute("SELECT category, COUNT(*) as count FROM patterns GROUP BY category")
            by_category = cursor.fetchall()
            
            conn.close()
            
            return {
                "total": total,
                "pending": pending,
                "approved": approved,
                "rejected": rejected,
                "by_category": dict(by_category)
            }
            
        except Exception as e:
            logger.error(f"Failed to get pattern stats: {e}")
            return {"total": 0, "pending": 0, "approved": 0, "rejected": 0, "by_category": {}}
    
    def clear_cache(self):
        self.history_cache.clear()
        
    def purge_old_patterns(self, days: int = 30):
        """Purge old patterns older than specified days."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            cursor.execute("DELETE FROM patterns WHERE updated_at < ? AND status = 'rejected'", (cutoff,))
            
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info(f"Purged {deleted} old rejected patterns")
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to purge old patterns: {e}")
            return 0

# Singleton instance
_learner_instance = None

def get_pattern_learner() -> PatternLearner:
    global _learner_instance
    if _learner_instance is None:
        _learner_instance = PatternLearner()
    return _learner_instance