import os
import json
import logging
from datetime import datetime
from src.services.logger_service import logger_service
from src.services.search_service import search_service
from src.llm_server import llm_instance
from config.settings import LOG_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_nightly_fact_check():
    logger.info("Starting nightly fact-check process...")
    
    # Get today's log file
    date_str = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(LOG_DIR, f"interactions_{date_str}.jsonl")
    draft_file = os.path.join(LOG_DIR, f"hermes_drafts_{date_str}.jsonl")
    
    if not os.path.exists(log_file):
        logger.info("No logs found for today. Skipping.")
        return

    interactions = []
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                interactions.append(json.loads(line))

    # Process each interaction for potential fact-checking
    # (In a real system, we'd filter for low-confidence or medical keywords)
    for interaction in interactions:
        user_prompt = interaction['messages'][0]['content']
        ai_response = interaction['messages'][1]['content']
        
        # Heuristic: Check for medical or procedure related questions
        if any(kw in user_prompt for kw in ["術後", "原理", "治療", "注意", "效果"]):
            logger.info(f"Fact-checking: {user_prompt[:30]}...")
            
            # 1. Search the web for grounding
            search_results = search_service.search(user_prompt, max_results=3)
            search_context = "\n".join([f"- {r['title']}: {r['body']}" for r in search_results])
            
            # 2. Ask Hermes to generate a "Corrected/Verified" draft
            verification_prompt = f"""
你是一個資深的醫學核稿員。請根據以下網頁搜尋到的外部醫學資料，檢核 AI 助理之前的回答是否準確且完整。
如果不準確，請生成一個修正後的版本（繁體中文，專業口吻）。

【使用者提問】
{user_prompt}

【AI 之前的回答】
{ai_response}

【網頁搜尋參考資料】
{search_context}

請提供你的核稿意見，並附上一個「建議修正版本」。
"""
            correction_draft = llm_instance.generate(verification_prompt, max_tokens=1024)
            
            # 3. Save as a draft for the doctor to review
            draft_entry = {
                "original_interaction": interaction,
                "search_results": search_results,
                "hermes_suggestion": correction_draft,
                "timestamp": datetime.now().isoformat()
            }
            
            with open(draft_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(draft_entry, ensure_ascii=False) + '\n')

    logger.info(f"Nightly fact-check complete. Drafts saved to {draft_file}")

if __name__ == "__main__":
    run_nightly_fact_check()
