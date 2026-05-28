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
            # Instructions updated to follow the new [Subject Header]\n[Question] format
            q_prompt = f"""你是一個病患提問模擬器。請針對主題『{topic}』，模擬出 3 個最常問的專業問題。

要求格式：
1. 第一行必須是『🚀 {topic}』。
2. 第二行才是具體的提問句。
3. 每個問題之間請用『---』分隔。
4. **絕對禁止**輸出任何關於「Thinking process」、「思考過程」或開場白。
5. 請直接從『🚀』開始輸出。

範例：
🚀 過敏性皮炎
我想知道這次發作的原因到底是什麼？以後還會有復發的風險嗎？
---
🚀 過敏性皮炎
這種病症在飲食上有什麼禁忌嗎？
"""
            questions_raw = llm_instance.generate(q_prompt, max_tokens=600)
            
            # Heavy cleaning
            if "<think>" in questions_raw:
                questions_raw = questions_raw.split("</think>")[-1].strip()
            
            # Remove common conversational prefixes
            noise_patterns = [
                "Here's a thinking process", 
                "Here are 3 common questions", 
                "以下是模擬提問", 
                "好的，為您模擬提問"
            ]
            for pattern in noise_patterns:
                if pattern in questions_raw:
                    # Try to find the first 🚀 after the pattern
                    start_idx = questions_raw.find("🚀")
                    if start_idx != -1:
                        questions_raw = questions_raw[start_idx:]
                    break

            # Split by separator
            raw_blocks = [b.strip() for b in questions_raw.split('---') if b.strip()]
            
            for block in raw_blocks[:3]:
                if len(block) < 10: continue
                
                # --- STRICT PARSING ---
                # 1. Split into lines
                lines = [l.strip() for l in block.split('\n') if l.strip()]
                
                # 2. Extract header and actual question
                header = f"🚀 {topic}"
                # Filter out lines that are instructions or noise
                noise_markers = ["format requirements", "line 2 must", "separate each", "thinking process", "🚀", "---"]
                question_lines = []
                for line in lines:
                    low_line = line.lower()
                    if any(marker in low_line for marker in noise_markers):
                        continue
                    question_lines.append(line)
                
                if not question_lines: continue
                
                # The first valid line is our actual question
                actual_question = question_lines[0]
                
                # --- NOISE & LENGTH FILTER ---
                # Remove backticks, dots, or other markdown junk
                actual_question = actual_question.replace('`', '').replace('*', '').strip()
                
                # Real medical questions should have substance. Discard junk.
                if len(actual_question) < 10 or actual_question in ["無", "不知道", "n/a"]:
                    logger.warning(f"Discarding noisy question: {actual_question}")
                    continue

                # Combine into the display format
                display_block = f"{header}\n{actual_question}"
                
                logger.info(f"Processing structured question:\nQ: {actual_question}")
                
                # 3. Use the existing Deep RAG to answer
                # IMPORTANT: Add topic context to the query to prevent generic greetings
                rag_query = f"關於『{topic}』的問題：{actual_question}"
                answer, confidence = self.rag.query_integrated(rag_query, route=category)
                
                # 4. Save to log
                entry = {
                    "type": f"proactive_{category}",
                    "service": topic,
                    "question": display_block, # Stored with header for UI
                    "answer": answer,
                    "confidence": confidence,
                    "timestamp": datetime.now().isoformat(),
                    "metadata": {
                        "source": "hermes_proactive_generator",
                        "category": category,
                        "route": category,
                        "raw_actual_question": actual_question # Hidden field for reference
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
