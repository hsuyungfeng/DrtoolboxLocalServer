import os
import json
import logging
import random
from datetime import datetime
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
        
        # Sample a few files to extract services from
        sample_files = random.sample(files, min(len(files), 10))
        
        for fname in sample_files:
            with open(os.path.join(SPECIAL_DATA_DIR, fname), 'r', encoding='utf-8') as f:
                content = f.read()[:2000]
                prompt = f"請從以下文件中識別出該診所提供的一個主要服務項目或療程名稱（例如：水飛梭、皮秒雷射、玻尿酸填補）。只需回答名稱，若無則回『無』：\n\n{content}"
                service = llm_instance.generate(prompt, max_tokens=50).strip()
                if service and service != "無" and len(service) < 20:
                    services.append(service)
        
        return list(set(services))

    def generate_proactive_qa(self):
        """Generates questions and answers for identified services."""
        services = self.scan_for_services()
        logger.info(f"Identified services for QA generation: {services}")
        
        for service in services:
            logger.info(f"Generating QA for: {service}")
            
            # 1. Generate 3 diverse patient questions
            q_prompt = f"針對醫美療程『{service}』，請模擬出 3 個病患最常問的專業問題（包含原理、術後、或效果）。請以繁體中文條列式輸出。"
            questions_raw = llm_instance.generate(q_prompt, max_tokens=300)
            
            # Simple parsing of lines
            questions = [line.strip().lstrip('123456789. ') for line in questions_raw.split('\n') if line.strip()]
            
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
