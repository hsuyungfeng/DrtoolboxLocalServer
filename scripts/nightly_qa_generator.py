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
from config.settings import DATA_DIR, SPECIAL_DATA_DIR, GENERAL_DATA_DIR, LOG_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QAGenerator:
    def __init__(self):
        self.rag = RAGEngine()
        
    def scan_for_topics(self, directory):
        """Scans a directory to identify potential topics/services."""
        topics = []
        files = [f for f in os.listdir(directory) if f.endswith('.txt')]
        if not files: return []
        
        # Priority patterns
        patterns = ["readme", "療程", "介紹", "手冊", "manual", "guideline", "診斷", "2025", "2026"]
        search_list = [f for f in files if any(p in f.lower() for p in patterns)]
        
        # Add some random ones too
        search_list += random.sample(files, min(len(files), 50))
        search_list = list(set(search_list)) # deduplicate
        
        for fname in search_list:
            try:
                with open(os.path.join(directory, fname), 'r', encoding='utf-8') as f:
                    content = f.read(5000).strip()
                    if len(content) < 200: continue
                    
                    prompt = f"""你是一個專業的醫學顧問。請從以下文件中識別出一個具體的『醫療主題』或『病症名稱』（如：糖尿病、高血壓、水飛梭、皮秒雷射）。

要求：
1. 只需回答名稱，不要包含思考過程或標籤。
2. 如果沒發現請回『無』。

內容：
{content}
"""
                    topic = llm_instance.generate(prompt, max_tokens=50).strip()
                    if "<think>" in topic: topic = topic.split("</think>")[-1].strip()
                    topic = topic.replace("主題：", "").replace("名稱：", "").replace("療程名稱：", "").strip()
                    
                    if topic and topic != "無" and len(topic) < 20 and "文件" not in topic:
                        topics.append(topic)
                        if len(topics) >= 15: break 
            except Exception: continue
        
        return list(set(topics))

    def generate_qa(self, category="special"):
        """Generates questions and answers for identified services/topics."""
        directory = SPECIAL_DATA_DIR if category == "special" else GENERAL_DATA_DIR
        topics = self.scan_for_topics(directory)
        logger.info(f"Identified {category} topics for QA generation: {topics}")
        
        output_file = os.path.join(LOG_DIR, f"proactive_qa_{category}_{datetime.now().strftime('%Y-%m-%d')}.jsonl")
        
        for topic in topics:
            logger.info(f"Generating {category} QA for: {topic}")
            
            # 1. Generate 3 diverse patient questions
            q_prompt = f"針對主題『{topic}』，請以病患的口吻模擬出 3 個最常問的專業問題。請直接輸出問題，每行一個，不要包含思考過程或標題。"
            questions_raw = llm_instance.generate(q_prompt, max_tokens=300)
            
            if "<think>" in questions_raw:
                questions_raw = questions_raw.split("</think>")[-1].strip()
            
            questions = [line.strip().lstrip('123456789. -*') for line in questions_raw.split('\n') if line.strip() and len(line.strip()) > 5]
            
            for question in questions[:3]:
                if len(question) < 5: continue
                
                logger.info(f"Processing generated question: {question}")
                
                # 2. Use the existing Deep RAG to answer
                # Pass the category as the route (special or general)
                answer, confidence = self.rag.query_integrated(question, route=category)
                
                # 3. Save to log
                entry = {
                    "type": f"proactive_{category}",
                    "service": topic,
                    "question": question,
                    "answer": answer,
                    "confidence": confidence,
                    "timestamp": datetime.now().isoformat(),
                    "metadata": {
                        "source": "hermes_proactive_generator",
                        "category": category,
                        "route": category
                    }
                }
                
                with open(output_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + '\n')
                    
        logger.info(f"Proactive {category} QA generation complete. Saved to {output_file}")

if __name__ == "__main__":
    gen = QAGenerator()
    # Run for both clinic-specific and general medical data
    gen.generate_qa("special")
    gen.generate_qa("general")
