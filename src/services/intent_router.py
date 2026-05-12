"""
Intent Router Service for Federated RAG

Classifies user queries to determine which knowledge base to search:
- general_medical (MEDICAL)
- clinic_specific (CLINICAL)
- both (BOTH)
"""

import logging
import requests
from typing import Literal

logger = logging.getLogger(__name__)

IntentType = Literal["MEDICAL", "CLINICAL", "BOTH"]

class IntentRouter:
    """Classifies queries using the local LLM to route RAG search."""
    
    def __init__(self, llama_url: str = "http://127.0.0.1:8081/v1/chat/completions"):
        self.llama_url = llama_url
        
    def classify(self, user_query: str) -> IntentType:
        """
        Classify the user's query into MEDICAL, CLINICAL, or BOTH.
        Uses keyword heuristics for speed, with LLM as optional refinement.
        """
        # Fast keyword-based classification (no LLM needed)
        query_lower = user_query.lower()
        
        medical_keywords = [
            "糖尿病", "高血壓", "感冒", "發燒", "頭痛", "症狀", "疾病", "治療",
            "藥", "手術", "癌症", "心臟", "肝", "肺", "免疫", "疫苗", "過敏",
            "diabetes", "fever", "symptom", "treatment", "cancer", "disease",
        ]
        clinical_keywords = [
            "掛號", "預約", "門診", "時間", "醫生", "費用", "價錢", "電話",
            "地址", "營業", "開門", "關門", "休診", "醫師", "排班", "看診",
            "病患", "病人", "診所", "設備", "檢查", "樓層", "櫃檯",
        ]
        
        has_medical = any(kw in user_query for kw in medical_keywords)
        has_clinical = any(kw in user_query for kw in clinical_keywords)
        
        if has_medical and has_clinical:
            return "BOTH"
        elif has_medical:
            return "MEDICAL"
        elif has_clinical:
            return "CLINICAL"
        
        # If no keywords match, try LLM classification
        prompt = f"""You are a query intent classifier for a clinic AI system.
Classify the user's query into exactly ONE of: MEDICAL, CLINICAL, BOTH.
User Query: "{user_query}"
Respond with ONLY ONE WORD: MEDICAL, CLINICAL, or BOTH."""
        
        try:
            response = requests.post(
                self.llama_url,
                json={
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 50,
                    "temperature": 0.0
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result_text = response.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip().upper()
                logger.debug(f"Intent Router raw output: {result_text}")
                
                if "BOTH" in result_text:
                    return "BOTH"
                if "MEDICAL" in result_text:
                    return "MEDICAL"
                if "CLINICAL" in result_text:
                    return "CLINICAL"
                
                logger.warning(f"Unexpected classification result '{result_text}'. Defaulting to BOTH.")
                return "BOTH"
            else:
                logger.warning(f"LLM API returned status {response.status_code}. Defaulting to BOTH.")
                return "BOTH"
                
        except Exception as e:
            logger.error(f"Intent classification failed: {e}. Defaulting to BOTH.")
            return "BOTH"

# Singleton instance
_router_instance = None

def get_intent_router() -> IntentRouter:
    """Get the singleton IntentRouter instance."""
    global _router_instance
    if _router_instance is None:
        _router_instance = IntentRouter()
    return _router_instance
