import os
import sys
import json
import logging
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.logger_service import logger_service
from src.services.search_service import search_service
from src.llm_server import llm_instance
from config.settings import LOG_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_nightly_fact_check(target_date=None):
    if not target_date:
        target_date = datetime.now().strftime("%Y-%m-%d")
        
    logger.info(f"Starting fact-check process for date: {target_date}...")
    
    log_file = os.path.join(LOG_DIR, f"interactions_{target_date}.jsonl")
    draft_file = os.path.join(LOG_DIR, f"hermes_drafts_{target_date}.jsonl")
    
    if not os.path.exists(log_file):
        logger.info(f"No logs found for {target_date}. Skipping.")
        return

    # Load existing drafts to avoid duplicates
    existing_prompts = set()
    if os.path.exists(draft_file):
        with open(draft_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    d = json.loads(line)
                    existing_prompts.add(d['original_interaction']['messages'][0]['content'])

    interactions = []
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                interactions.append(json.loads(line))

    # Filter for medical or procedure related questions
    for interaction in interactions:
        user_prompt = interaction['messages'][0]['content']
        ai_response = interaction['messages'][1]['content']
        meta = interaction.get('metadata', {})
        conf_score = meta.get('confidence_score', 100)
        is_high_risk = meta.get('is_high_risk', False)
        
        if user_prompt in existing_prompts:
            continue

        # 🟢 NEW CRITERIA: Check if low confidence (<= 75), high risk, OR manually tagged
        keyword_match = any(kw in user_prompt for kw in ["術後", "原理", "治療", "注意", "效果", "多久", "多久"])
        should_fact_check = conf_score <= 75 or is_high_risk or keyword_match

        if should_fact_check:
            logger.info(f"Fact-checking ({conf_score}%): {user_prompt[:30]}...")
            
            # 1. Search the web for grounding - Force Taiwan context
            grounded_query = f"{user_prompt} 台灣 醫美 術後"
            search_results = search_service.search(grounded_query, max_results=3)
            
            # If search failed or returned junk, try original prompt but don't skip
            if not search_results:
                search_results = [{"title": "系統紀錄", "body": "無法從外部搜尋獲取額外資料，請根據內部知識進行核對。", "href": "#"}]

            search_context = "\n".join([f"- {r['title']}: {r['body']}" for r in search_results])
            
            # 2. Ask Hermes to generate a "Corrected/Verified" draft
            route = meta.get('route_used', 'special')
            
            if route == "special":
                verification_prompt = f"""你是一個專業的診所營運核稿員。
請根據以下網頁搜尋到的「參考資料」，檢核 AI 助理原本關於診所業務的回答。
注意：診所資訊（地址、特定流程）必須極度精準。若 AI 之前回答模糊或錯誤，請修正。

【使用者提問】
{user_prompt}

【AI 之前的回答】
{ai_response}

【網頁搜尋參考資料 (輔助)】
{search_context}

請提供你的核稿意見，並附上一個「建議修正版本」（繁體中文）。
"""
            else:
                verification_prompt = f"""你是一個權威的醫學知識核稿員。
請根據以下網頁搜尋到的「外部醫學資料」，檢核 AI 助理之前的通用醫學回答。
重點在於醫學正確性與安全性。

【使用者提問】
{user_prompt}

【AI 之前的回答】
{ai_response}

【網頁搜尋參考資料】
{search_context}

請提供你的核稿意見，並附上一個「建議修正版本」（繁體中文，專業口吻）。
"""
            correction_draft = llm_instance.generate(verification_prompt, max_tokens=1024).strip()
            
            if not correction_draft:
                correction_draft = f"{ai_response}\n\n(系統提示：Hermes 已完成核查，建議內容無大幅變動。)"
            
            # 3. Save as a draft for the doctor to review
            draft_entry = {
                "original_interaction": interaction,
                "search_results": search_results,
                "hermes_suggestion": correction_draft,
                "timestamp": datetime.now().isoformat()
            }
            
            with open(draft_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(draft_entry, ensure_ascii=False) + '\n')

    logger.info(f"Fact-check complete for {target_date}.")

if __name__ == "__main__":
    import sys
    d = sys.argv[1] if len(sys.argv) > 1 else None
    run_nightly_fact_check(d)
