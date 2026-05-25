import os
import sys
import json
import logging
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.llm_server import llm_instance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VERIFIED_DATA_PATH = "data/verified_training_data.jsonl"
OUTPUT_PATH = "data/evaluation/articles_to_post.json"

def convert_qa_to_article():
    if not os.path.exists(VERIFIED_DATA_PATH):
        logger.error(f"Verified data not found at {VERIFIED_DATA_PATH}")
        return

    articles = []
    
    with open(VERIFIED_DATA_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    print(f"🔄 Converting {len(lines)} QA pairs into professional articles...")

    for i, line in enumerate(lines):
        try:
            entry = json.loads(line)
            user_msg = entry['messages'][0]['content']
            ai_msg = entry['messages'][1]['content']
            service = entry.get('metadata', {}).get('service', '醫美療程')
            
            print(f"   [{i+1}/{len(lines)}] Processing: {user_msg[:20]}...")

            prompt = f"""你是一個專業的醫美診所文案撰寫員。
請根據以下的一組問答（QA），將其改寫成一篇適合發布在「診所機器人知識庫」的專業文章。

【寫作指南】
1. 標題：必須清楚、主題單一（例如：皮秒雷射術後照顧注意事項）。
2. 類別：請根據內容判斷（例如：術後照顧、療程原理、預約資訊）。
3. 內容：請使用「自然語言散文」書寫，避免表格。語氣要專業、親切且有權威性。
4. 嚴禁報價：絕對不能出現金錢數字。

【原始 QA】
問：{user_msg}
答：{ai_msg}

請直接回傳 JSON 格式如下：
{{
    "title": "文章標題",
    "category": "文章類別",
    "content": "散文形式的文章內容"
}}
"""
            res_raw = llm_instance.generate(prompt, max_tokens=1500).strip()
            
            # Handle thinking tags and markdown
            if "<think>" in res_raw:
                res_raw = res_raw.split("</think>")[-1].strip()
            if "```json" in res_raw:
                res_raw = res_raw.split("```json")[1].split("```")[0].strip()
            elif "```" in res_raw:
                res_raw = res_raw.split("```")[1].split("```")[0].strip()
            
            article_data = json.loads(res_raw)
            articles.append(article_data)
            
        except Exception as e:
            logger.error(f"Failed to process entry {i}: {e}")

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=4)

    print(f"\n✅ Successfully generated {len(articles)} articles!")
    print(f"📄 File saved to: {OUTPUT_PATH}")

if __name__ == "__main__":
    convert_qa_to_article()
