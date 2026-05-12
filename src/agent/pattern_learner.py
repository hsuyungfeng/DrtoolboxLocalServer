"""
Pattern Learner

Analyzes staff conversations to identify frequently asked questions or repetitive tasks.
Generates 'Candidate Skills' that can be approved to become Auto-Skills.
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class PatternLearner:
    """Monitors chat history and suggests Auto-Skills."""
    
    def __init__(self):
        self.history_cache = []
        self.pattern_threshold = 3  # Suggest a skill after seeing a pattern 3 times
        
    def log_query(self, query: str):
        """Log a user query for pattern analysis."""
        # Simple placeholder for pattern matching logic
        # In a real system, this would use embeddings to find semantic duplicates
        self.history_cache.append(query)
        logger.info(f"Logged query for pattern analysis: {query}")
        
    def extract_candidates(self) -> List[Dict[str, Any]]:
        """
        Analyze recent history and extract candidate skills.
        Returns a list of candidate dictionaries.
        """
        # Very basic word frequency / exact match analysis
        counts = {}
        for q in self.history_cache:
            q_lower = q.lower().strip()
            counts[q_lower] = counts.get(q_lower, 0) + 1
            
        candidates = []
        for q, count in counts.items():
            if count >= self.pattern_threshold:
                candidates.append({
                    "pattern": q,
                    "frequency": count,
                    "suggested_name": f"auto_skill_{len(candidates) + 1}",
                    "description": f"Auto-generated skill for pattern: {q}"
                })
                
        return candidates
    
    def clear_cache(self):
        self.history_cache.clear()

# Singleton instance
_learner_instance = None

def get_pattern_learner() -> PatternLearner:
    global _learner_instance
    if _learner_instance is None:
        _learner_instance = PatternLearner()
    return _learner_instance
