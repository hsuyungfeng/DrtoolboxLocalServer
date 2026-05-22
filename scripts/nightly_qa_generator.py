import os
import sys
import json
import logging
import random
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.llm_server import llm_instance
from src.rag_engine import RAGEngine
from config.settings import DATA_DIR, SPECIAL_DATA_DIR, LOG_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QAGenerator:
    def __init__(self):
        self.rag = RAGEngine()
        self.output_file = os.path.join(LOG_DIR, f"proactive_qa_{datetime.now().strftime('%Y-%m-%d')}.jsonl")
        
    def scan_for_services(self):
        """Scans clinic documents to identify potential service items/procedures."""
        services = []
        files = [f for f in os.listdir(SPECIAL_DATA_DIR) if f.endswith('.txt')]
        if not files: return []
        
        # Priority patterns
        patterns = ["readme", "療程", "介紹", "手冊", "manual", "2025", "2026"]
        search_list = [f for f in files if any(p in f.lower() for p in patterns)]
        
        # Add some random ones too
        search_list += random.sample(files, min(len(files), 50))
        search_list = list(set(search_list)) # deduplicate
        
        for fname in search_list:
            try:
                with open(os.path.join(SPECIAL_DATA_DIR, fname), 'r', encoding='utf-8') as f:
                    content = f.read(5000).strip()
                    if len(content) < 200: continue
                    
                    prompt = f"""你是一個專業的醫美診所顧問。請從以下文件中識別出該診所提供的一個主要『服務項目』或『療程名稱』（如：水飛梭、皮秒雷射、音波拉提、微創痔瘡手術）。

要求：
1. 只需回答名稱，不要包含思考過程或標籤。
2. 如果沒發現請回『無』。

內容：
{content}
"""
                    service = llm_instance.generate(prompt, max_tokens=50).strip()
                    if "<think>" in service: service = service.split("</think>")[-1].strip()
                    service = service.replace("療程名稱：", "").replace("名稱：", "").replace("服務項目：", "").strip()
                    
                    if service and service != "無" and len(service) < 20 and "文件" not in service:
                        services.append(service)
                        if len(services) >= 15: break 
            except Exception: continue
        
        return list(set(services))

    def generate_proactive_qa(self):
        """Generates questions and answers for identified services."""
        services = self.scan_for_services()
        logger.info(f"Identified services for QA generation: {services}")
        
        for service in services:
            logger.info(f"Generating QA for: {service}")
            
            # 1. Generate 3 diverse patient questions
            q_prompt = f"針對醫美療程『{service}』，請以病患的口吻模擬出 3 個最常問的專業問題（包含原理、術後、或效果）。請直接輸出問題，每行一個，不要包含思考過程或標題。"
            questions_raw = llm_instance.generate(q_prompt, max_tokens=300)
            
            # Remove thinking tags if present
            if "<think>" in questions_raw:
                questions_raw = questions_raw.split("</think>")[-1].strip()
            
            # Simple parsing of lines
            questions = [line.strip().lstrip('123456789. -*') for line in questions_raw.split('\n') if line.strip() and len(line.strip()) > 5]
            
            for question in questions[:3]:
                if len(question) < 5: continue
                
                logger.info(f"Processing generated question: {question}")
                
                # 2. Use the existing Deep RAG to answer the question
                # (This will use our PageIndex summaries and text chunks)
                answer = self.rag.query_integrated(question)
                
                # 3. Save to a special 'Proactive' log for doctor review
                entry = {
                    "type": "proactive_simulated",
                    "service": service,
                    "question": question,
                    "answer": answer,
                    "timestamp": datetime.now().isoformat(),
                    "metadata": {
                        "source": "hermes_proactive_generator",
                        "model": "llama-qwen"
                    }
                }
                
                with open(self.output_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + '\n')
                    
        logger.info(f"Proactive QA generation complete. Saved to {self.output_file}")

if __name__ == "__main__":
    gen = QAGenerator()
    gen.generate_proactive_qa()
