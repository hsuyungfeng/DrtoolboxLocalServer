"""
Hermes Agent Core

This module defines the core HermesAgent class that interacts with the
local llama.cpp server, the HIS database, and the Federated RAG.
"""

import json
import logging
import requests
from typing import Dict, Any, List, Optional

try:
    from src.services.intent_router import get_intent_router
except ImportError:
    get_intent_router = None
    
try:
    from src.api.routes.rag import get_query_answer
except ImportError:
    get_query_answer = None
    
try:
    from src.llm.cloud_backend import get_cloud_backend
except ImportError:
    get_cloud_backend = None

from src.db.his_connection import HISConnection

logger = logging.getLogger(__name__)

class HermesAgent:
    """Core Agent for DrtoolboxLocalServer"""
    
    def __init__(self, llama_url: str = "http://127.0.0.1:8081/v1/chat/completions"):
        self.llama_url = llama_url
        try:
            self.intent_router = get_intent_router() if get_intent_router else None
        except:
            self.intent_router = None
        try:
            self.rag_engine = get_query_answer() if get_query_answer else None
        except:
            self.rag_engine = None
        self.his_conn = HISConnection()
        
        # HIS Context - loaded on initialization
        self.his_context = {}
        self.context_loaded_at = None
        self.context_refresh_interval = 1800  # 30 minutes
        
    def init_with_context(self) -> bool:
        """
        Initialize agent with full HIS context.
        Returns True if successful, False otherwise.
        """
        try:
            # Load clinic info
            clinic_info = self.his_conn.execute(
                "SELECT clinic_name_chinese, staff_count, num_beds, specialties, "
                "address, phone, email FROM clinic_info WHERE is_active = 1"
            )
            
            if clinic_info:
                self.his_context['clinic_info'] = clinic_info[0]
            
            # Load patient summary stats
            try:
                patient_stats = self.his_conn.execute(
                    "SELECT COUNT(*) as total_patients FROM clinic_daily_log"
                )
                self.his_context['patient_stats'] = {
                    'total_records': patient_stats[0]['total_patients'] if patient_stats else 0
                }
            except:
                self.his_context['patient_stats'] = {'total_records': 0}
            
            # Load recent appointments (last 10)
            try:
                recent_appts = self.his_conn.execute(
                    "SELECT * FROM clinic_daily_log ORDER BY created_at DESC LIMIT 10"
                )
                self.his_context['recent_appointments'] = recent_appts if recent_appts else []
            except:
                self.his_context['recent_appointments'] = []
            
            # Load staff list
            try:
                staff = self.his_conn.execute(
                    "SELECT name, role FROM clinic_staff WHERE is_active = 1"
                )
                self.his_context['staff_list'] = staff if staff else []
            except:
                self.his_context['staff_list'] = []
            
            # Check connection health
            self.his_context['connection_healthy'] = True
            
            import datetime
            self.context_loaded_at = datetime.datetime.now()
            
            logger.info("HermesAgent HIS context loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load HIS context: {e}")
            self.his_context['connection_healthy'] = False
            return False
    
    def refresh_context(self) -> bool:
        """
        Manually trigger context refresh.
        """
        logger.info("Refreshing HIS context...")
        return self.init_with_context()
    
    def get_context_status(self) -> Dict[str, Any]:
        """
        Get current context status including health and last refresh time.
        """
        import datetime
        return {
            'healthy': self.his_context.get('connection_healthy', False),
            'clinic_name': self.his_context.get('clinic_info', {}).get('clinic_name_chinese', 'N/A'),
            'staff_count': len(self.his_context.get('staff_list', [])),
            'patient_records': self.his_context.get('patient_stats', {}).get('total_records', 0),
            'last_refresh': self.context_loaded_at.isoformat() if self.context_loaded_at else None,
            'refresh_interval_sec': self.context_refresh_interval
        }
    
    def _check_and_refresh_context(self):
        """
        Internal: Check if context needs refresh and refresh if needed.
        Called automatically before each chat interaction.
        """
        import datetime
        if not self.context_loaded_at:
            self.init_with_context()
            return
            
        elapsed = (datetime.datetime.now() - self.context_loaded_at).total_seconds()
        if elapsed > self.context_refresh_interval:
            logger.info("Context stale, auto-refreshing...")
            self.init_with_context()
        
    def chat(self, user_query: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Process a user query, determine context (HIS or RAG), and return a response.
        """
        # Auto-refresh context if needed
        self._check_and_refresh_context()
        
        if history is None:
            history = []
            
        # 1. Intent Classification
        intent = self.intent_router.classify(user_query)
        logger.info(f"HermesAgent intent classification: {intent}")
        
        system_prompt = "You are Hermes, an intelligent clinical assistant for Drtoolbox. You help clinic staff with medical knowledge and operational tasks."
        context_text = ""
        
        # 2. Gather Context from RAG
        if intent in ["MEDICAL", "CLINICAL", "BOTH"]:
            # Retrieve from Federated RAG
            try:
                rag_response = self.rag_engine.query(user_query, top_k=3, use_llm=False)
                if rag_response and hasattr(rag_response, 'answer') and rag_response.answer:
                    context_text += f"Knowledge Base Information:\n{rag_response.answer}\n\n"
            except Exception as e:
                logger.error(f"RAG engine query failed: {e}")
                
        # 3. Use cached HIS context when needed
        if "patient" in user_query.lower() or "看診" in user_query or "病患" in user_query or intent in ["MEDICAL", "CLINICAL", "BOTH"]:
            # Use cached context from init_with_context
            if self.his_context.get('clinic_info'):
                info = self.his_context['clinic_info']
                context_text += (
                    f"HIS 診所資訊：\n"
                    f"- 診所名稱：{info.get('clinic_name_chinese', 'N/A')}\n"
                    f"- 員工人數：{info.get('staff_count', 'N/A')} 人\n"
                    f"- 病床數：{info.get('num_beds', 'N/A')} 床\n"
                    f"- 專科：{info.get('specialties', 'N/A')}\n\n"
                )
            
            # Add patient stats if available
            if self.his_context.get('patient_stats'):
                records = self.his_context['patient_stats'].get('total_records', 0)
                if records > 0:
                    context_text += f"目前記錄總數：{records} 筆\n\n"
                
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
        # Initialize with HIS context on first creation
        _agent_instance.init_with_context()
    return _agent_instance
