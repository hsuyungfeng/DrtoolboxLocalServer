"""
Hermes Agent Core

This module defines the core HermesAgent class that interacts with the
local llama.cpp server, the HIS database, and the Federated RAG.
"""

import json
import logging
import requests
from typing import Dict, Any, List, Optional

from src.services.intent_router import get_intent_router
from src.api.routes.rag import get_query_answer
from src.db.his_connection import HISConnection
from src.llm.cloud_backend import get_cloud_backend

logger = logging.getLogger(__name__)

class HermesAgent:
    """Core Agent for DrtoolboxLocalServer"""
    
    def __init__(self, llama_url: str = "http://127.0.0.1:8081/v1/chat/completions"):
        self.llama_url = llama_url
        self.intent_router = get_intent_router()
        self.rag_engine = get_query_answer()
        self.his_conn = HISConnection()
        
    def chat(self, user_query: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Process a user query, determine context (HIS or RAG), and return a response.
        """
        if history is None:
            history = []
            
        # 1. Intent Classification
        intent = self.intent_router.classify(user_query)
        logger.info(f"HermesAgent intent classification: {intent}")
        
        system_prompt = "You are Hermes, an intelligent clinical assistant for Drtoolbox. You help clinic staff with medical knowledge and operational tasks."
        context_text = ""
        
        # 2. Gather Context
        if intent in ["MEDICAL", "CLINICAL", "BOTH"]:
            # Retrieve from Federated RAG
            try:
                rag_response = self.rag_engine.query(user_query, top_k=3, use_llm=False)
                if rag_response and hasattr(rag_response, 'answer') and rag_response.answer:
                    context_text += f"Knowledge Base Information:\n{rag_response.answer}\n\n"
            except Exception as e:
                logger.error(f"RAG engine query failed: {e}")
                
        # 3. Check if HIS context is needed (simple heuristic for now)
        if "patient" in user_query.lower() or "看診" in user_query or "病患" in user_query:
            try:
                # Query clinic info and daily log for relevant context
                clinic_stats = self.his_conn.execute("SELECT clinic_name_chinese, staff_count, num_beds, specialties FROM clinic_info WHERE is_active = 1")
                if clinic_stats:
                    info = clinic_stats[0]
                    context_text += (
                        f"HIS 診所資訊：\n"
                        f"- 診所名稱：{info.get('clinic_name_chinese', 'N/A')}\n"
                        f"- 員工人數：{info.get('staff_count', 'N/A')} 人\n"
                        f"- 病床數：{info.get('num_beds', 'N/A')} 床\n"
                        f"- 專科：{info.get('specialties', 'N/A')}\n\n"
                    )
                
                # Check today's appointments
                daily_stats = self.his_conn.execute("SELECT COUNT(*) as count FROM clinic_daily_log")
                log_count = daily_stats[0]['count'] if daily_stats else 0
                if log_count > 0:
                    context_text += f"今日已記錄：{log_count} 筆日誌\n\n"
            except Exception as e:
                logger.error(f"HIS connection error: {e}")
                
        # 4. Construct Prompt
        if context_text:
            system_prompt += f"\n\nHere is some context to help you answer:\n{context_text}"
            
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_query})
        
        # 5. Call LLM (try local first, fallback to cloud)
        try:
            # Try local llama.cpp first
            try:
                response = requests.post(
                    self.llama_url,
                    json={
                        "messages": messages,
                        "max_tokens": 1024,
                        "temperature": 0.3
                    },
                    timeout=120
                )

                if response.status_code == 200:
                    return response.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                else:
                    logger.warning(f"Local LLM error {response.status_code}, falling back to cloud")

            except (requests.ConnectionError, requests.Timeout) as e:
                logger.warning(f"Local LLM unavailable ({type(e).__name__}), falling back to cloud API")

            # Fallback to cloud backend
            backend = get_cloud_backend()
            result = backend.complete(messages, max_tokens=1024, temperature=0.3)
            return result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

        except Exception as e:
            logger.error(f"HermesAgent chat failed: {e}")
            return "抱歉，系統發生內部錯誤。"

# Singleton instance
_agent_instance = None

def get_hermes_agent() -> HermesAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = HermesAgent()
    return _agent_instance
