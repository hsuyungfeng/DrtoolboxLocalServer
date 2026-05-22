"""
Hermes Agent Core - Unified Intelligence System

Consolidates HermesAgent and HermesRouter into a single class with:
- Intent Routing (Special/General)
- Hybrid RAG (SQL + PageIndex + SimpleIndex)
- HIS Context Awareness
"""

import json
import logging
import requests
import datetime
import threading
from typing import Dict, Any, List, Optional, Tuple
from src.db.his_connection import HISConnection
from src.rag_engine import RAGEngine
from src.llm_server import llm_instance

logger = logging.getLogger(__name__)

class HermesAgent:
    """Consolidated Agent for DrtoolboxLocalServer"""
    
    def __init__(self, llama_url: str = "http://127.0.0.1:8080/v1/chat/completions"):
        self.llama_url = llama_url
        self.llm = llm_instance
        self.rag = RAGEngine()
        self.his_conn = HISConnection()
        
        # Context management
        self.his_context = {}
        self.context_loaded_at = None
        self.context_refresh_interval = 1800 

        # Initial background data load
        threading.Thread(target=self._initial_ingest, daemon=True).start()
        
    def _initial_ingest(self):
        """Warm up the RAG engine on startup."""
        from src.data_loader import get_special_data, get_general_data
        logger.info("Initializing unified RAG memory...")
        special_docs = get_special_data(self.rag)
        if special_docs: self.rag.ingest_special_data(special_docs)
        general_docs = get_general_data(self.rag)
        if general_docs: self.rag.ingest_general_data(general_docs)
        logger.info("Unified RAG initialization complete.")

    def init_with_context(self) -> bool:
        """Loads clinic info and stats from HIS."""
        try:
            clinic_info = self.his_conn.execute("SELECT * FROM clinic_info WHERE is_active = 1 LIMIT 1")
            if clinic_info: self.his_context['clinic_info'] = clinic_info[0]
            
            patient_stats = self.his_conn.execute("SELECT COUNT(*) as total FROM clinic_daily_log")
            self.his_context['patient_records'] = patient_stats[0]['total'] if patient_stats else 0
            
            self.context_loaded_at = datetime.datetime.now()
            return True
        except Exception as e:
            logger.error(f"HIS load failed: {e}")
            return False

    def determine_route(self, prompt: str) -> str:
        """Decides which knowledge base to prioritize."""
        router_prompt = f"""<|im_start|>system
You are a clinic AI. Classify the user query as 'special' (clinic-specific procedures, marketing, hours) or 'general' (general medical knowledge, healthy tips). Reply only with one word.
<|im_end|>
<|im_start|>user
{prompt}
<|im_end|>
<|im_start|>assistant
"""
        try:
            res = self.llm.generate(router_prompt, max_tokens=10).strip().lower()
            return "special" if "special" in res else "general"
        except:
            return "special"

    def chat(self, user_query: str, history: Optional[List[Dict[str, str]]] = None) -> Tuple[str, str]:
        """Core chat loop with hybrid reasoning."""
        if not self.context_loaded_at: self.init_with_context()
        
        # 1. Routing
        route = self.determine_route(user_query)
        logger.info(f"Unified Hermes routing: {route}")
        
        # 2. Hybrid Reasoning (RAG + SQL)
        try:
            response = self.rag.query_integrated(user_query)
        except Exception as e:
            logger.error(f"Chat reasoning failed: {e}")
            response = "抱歉，我現在處理您的請求時遇到一點困難。請稍後再試。"
            
        return response, route

    def get_context_status(self) -> Dict[str, Any]:
        return {
            'healthy': self.context_loaded_at is not None,
            'clinic_name': self.his_context.get('clinic_info', {}).get('clinic_name_chinese', 'N/A'),
            'patient_records': self.his_context.get('patient_records', 0),
            'last_refresh': self.context_loaded_at.isoformat() if self.context_loaded_at else None
        }

# Singleton
_agent_instance = None

def get_hermes_agent() -> HermesAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = HermesAgent()
    return _agent_instance
