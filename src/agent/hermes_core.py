"""
Hermes Agent Core - Unified Intelligence System

Consolidates HermesAgent and HermesRouter into a single class with:
- Intent Routing (Special/General)
- Hybrid RAG (SQL + PageIndex + SimpleIndex)
- HIS Context Awareness
- High-Risk Medical Symptom Detection
"""

import json
import logging
import requests
import datetime
import threading
import re
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

    def _check_high_risk(self, text: str) -> bool:
        """Checks for high-risk medical keywords requiring staff escalation."""
        risk_keywords = [
            "劇烈疼痛", "非常痛", "痛到受不了", "發黑", "變黑", "變白", "發紫", "流膿", 
            "化膿", "視力模糊", "看不清楚", "呼吸困難", "喘不過氣", "發燒", "高燒", "沒呼吸"
        ]
        return any(k in text for k in risk_keywords)

    def _ocr_base64_image(self, image_data: str) -> str:
        """Helper to OCR an image provided as base64."""
        import base64
        import io
        from PIL import Image
        import pytesseract
        try:
            img_bytes = base64.b64decode(image_data)
            img = Image.open(io.BytesIO(img_bytes))
            try:
                text = pytesseract.image_to_string(img, lang='chi_tra+eng')
            except:
                text = pytesseract.image_to_string(img)
            return text.strip()
        except Exception as e:
            logger.error(f"Local OCR fallback failed: {e}")
            return ""

    def chat_stream(self, user_query: str, history: Optional[List[Dict[str, str]]] = None, image_data: Optional[str] = None):
        """Core chat loop with hybrid reasoning (Streaming + Vision support + Risk Detection + Self-Scoring)."""
        if not self.context_loaded_at: self.init_with_context()
        
        # 1. Routing & Risk Detection
        route = self.determine_route(user_query)
        is_high_risk = self._check_high_risk(user_query)
        logger.info(f"Unified Hermes routing (stream): {route} (High Risk: {is_high_risk})")
        
        # 2. Hybrid Reasoning
        try:
            # Yield metadata including risk status
            yield f"data: {json.dumps({'route_used': route, 'is_high_risk': is_high_risk})}\n\n"
            
            is_fallback = False
            full_response = ""
            confidence_score = 0
            
            for chunk in self.rag.query_integrated_stream(user_query, image_data=image_data):
                if chunk == "ERROR_VISION_NOT_SUPPORTED":
                    is_fallback = True
                    break
                
                if not chunk: continue

                # Check for end-of-stream confidence score
                if chunk.startswith("__CONFIDENCE_SCORE__"):
                    try:
                        confidence_score = int(chunk.replace("__CONFIDENCE_SCORE__", ""))
                    except: pass
                    break

                full_response += chunk
                yield f"data: {json.dumps({'content': chunk})}\n\n"
            
            if is_fallback:
                logger.warning("Local LLM does not support vision. Performing local OCR and falling back to text-only.")
                ocr_text = self._ocr_base64_image(image_data) if image_data else ""
                
                msg = '⚠️ **系統提示**：目前的本地 AI 模型尚未配置「視覺辨識」組件（mmproj），但我已嘗試透過光學字元辨識 (OCR) 讀取您的照片內容。\n\n'
                if ocr_text:
                    msg += f"**[辨識出的文字內容]**：\n> {ocr_text[:300]}...\n\n---\n\n"
                elif image_data:
                    msg += "（很抱歉，我無法直接看到照片，且 OCR 也無法從中提取有效文字，請您改用文字描述。）\n\n---\n\n"
                
                yield f"data: {json.dumps({'content': msg})}\n\n"
                
                enhanced_query = user_query
                if ocr_text:
                    enhanced_query = f"[附件圖片辨識文字：{ocr_text}] {user_query}"
                
                for chunk in self.rag.query_integrated_stream(enhanced_query, image_data=None):
                    if not chunk: continue
                    if chunk.startswith("__CONFIDENCE_SCORE__"):
                        try: confidence_score = int(chunk.replace("__CONFIDENCE_SCORE__", ""))
                        except: pass
                        break
                    full_response += chunk
                    yield f"data: {json.dumps({'content': chunk})}\n\n"

            # Send final score
            yield f"data: {json.dumps({'confidence_score': confidence_score})}\n\n"
            
            # 3. Log the interaction for curation
            from src.services.logger_service import logger_service
            logger_service.log_interaction(
                user_id="dashboard_user",
                prompt=user_query,
                response=full_response,
                route_used=route,
                is_high_risk=is_high_risk,
                confidence_score=confidence_score
            )
            
            # 4. Auto-Curation Logic
            if confidence_score >= 85 and not is_high_risk:
                logger.info(f"Auto-archiving high-confidence response ({confidence_score}%)")
                logger_service.save_correction(
                    {"messages": [{"role": "user", "content": user_query}]},
                    full_response
                )
                # Note: Removal from source files requires knowing the interaction timestamp
                # which is generated inside logger_service.log_interaction.
                # For now, we rely on the UI refresh to show it's gone if filters are applied.
            
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"Chat streaming failed: {e}")
            yield f"data: {json.dumps({'content': '抱歉，我現在處理您的請求時遇到一點困難。'})}\n\n"
            yield "data: [DONE]\n\n"

    def chat(self, user_query: str, history: Optional[List[Dict[str, str]]] = None, image_data: Optional[str] = None) -> Tuple[str, str, bool, int]:
        """Core chat loop with hybrid reasoning (Vision support + Risk Detection + Self-Scoring)."""
        if not self.context_loaded_at: self.init_with_context()
        
        # 1. Routing & Risk Detection
        route = self.determine_route(user_query)
        is_high_risk = self._check_high_risk(user_query)
        logger.info(f"Unified Hermes routing: {route} (High Risk: {is_high_risk})")
        
        # 2. Hybrid Reasoning
        try:
            response, confidence_score = self.rag.query_integrated(user_query, image_data=image_data)
            if response == "ERROR_VISION_NOT_SUPPORTED":
                logger.warning("Local LLM does not support vision. Falling back to OCR + Text.")
                ocr_text = self._ocr_base64_image(image_data) if image_data else ""
                
                prefix = "⚠️ **系統提示**：目前的本地 AI 模型尚未配置「視覺辨識」組件（mmproj）。\n\n"
                enhanced_query = user_query
                if ocr_text:
                    prefix += f"**[辨識出的文字內容]**：\n> {ocr_text[:300]}...\n\n---\n\n"
                    enhanced_query = f"[附件圖片辨識文字：{ocr_text}] {user_query}"
                elif image_data:
                    prefix += "（我無法看到照片，且無法辨識出文字，請用文字描述。）\n\n"

                response, confidence_score = self.rag.query_integrated(enhanced_query, image_data=None)
                response = prefix + response
                
            # Auto-Curation
            if confidence_score >= 85 and not is_high_risk:
                from src.services.logger_service import logger_service
                logger_service.save_correction(
                    {"messages": [{"role": "user", "content": user_query}]},
                    response
                )
                
        except Exception as e:
            logger.error(f"Chat reasoning failed: {e}")
            response = "抱歉，我現在處理您的請求時遇到一點困難。請稍後再試。"
            confidence_score = 0
            
        return response, route, is_high_risk, confidence_score

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
